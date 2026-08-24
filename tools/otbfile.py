"""Lectura/escritura del contenedor binario de nodos que usa el servidor.

Tanto items.otb como los mapas .otbm usan el mismo formato: un identificador de
4 bytes seguido de un arbol de nodos delimitados por marcadores.

    START  = 0xFE   abre un nodo, el byte siguiente es su tipo
    END    = 0xFF   cierra el nodo actual
    ESCAPE = 0xFD   el byte siguiente es literal, no un marcador

Valores tomados de src/fileloader.h. El parser del servidor esta en
src/fileloader.cpp (OTB::Loader::parseTree).
"""

import struct

ESCAPE = 0xFD
START = 0xFE
END = 0xFF


class Node:
    __slots__ = ("type", "props", "children")

    def __init__(self, node_type=0, props=b"", children=None):
        self.type = node_type
        self.props = props
        self.children = children if children is not None else []


def parse(path):
    """Devuelve (identificador, nodo_raiz) del archivo indicado."""
    with open(path, "rb") as fh:
        blob = fh.read()

    identifier = blob[:4]
    pos = 4
    if blob[pos] != START:
        raise ValueError("no empieza con un marcador de nodo")
    pos += 1

    root = Node(blob[pos])
    pos += 1
    stack = [root]
    buf = bytearray()

    while pos < len(blob):
        byte = blob[pos]
        if byte == START:
            # Los props de un nodo son los bytes previos a su primer hijo.
            # Igual que OTB::Loader::parseTree, solo se fijan una vez.
            if not stack[-1].children:
                stack[-1].props = bytes(buf)
            buf = bytearray()
            pos += 1
            child = Node(blob[pos])
            stack[-1].children.append(child)
            stack.append(child)
        elif byte == END:
            if not stack[-1].children:
                stack[-1].props = bytes(buf)
            buf = bytearray()
            stack.pop()
        elif byte == ESCAPE:
            pos += 1
            buf.append(blob[pos])
        else:
            buf.append(byte)
        pos += 1

    return identifier, root


def _escape(data):
    out = bytearray()
    for byte in data:
        if byte in (ESCAPE, START, END):
            out.append(ESCAPE)
        out.append(byte)
    return bytes(out)


def _write_node(out, node):
    out.append(START)
    out.append(node.type)
    out += _escape(node.props)
    for child in node.children:
        _write_node(out, child)
    out.append(END)


def write(path, identifier, root):
    """Serializa el arbol de nodos al archivo indicado."""
    out = bytearray(identifier)
    _write_node(out, root)
    with open(path, "wb") as fh:
        fh.write(bytes(out))


class Reader:
    """Lector secuencial sobre los props de un nodo."""

    def __init__(self, data):
        self.data = data
        self.pos = 0

    def left(self):
        return len(self.data) - self.pos

    def u8(self):
        value = self.data[self.pos]
        self.pos += 1
        return value

    def u16(self):
        value = struct.unpack_from("<H", self.data, self.pos)[0]
        self.pos += 2
        return value

    def u32(self):
        value = struct.unpack_from("<I", self.data, self.pos)[0]
        self.pos += 4
        return value

    def raw(self, count):
        value = self.data[self.pos:self.pos + count]
        self.pos += count
        return value
