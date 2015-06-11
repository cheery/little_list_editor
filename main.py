from PyQt4 import QtGui, QtCore
from PyQt4.QtGui import QPalette, QColor
from PyQt4.QtCore import QPointF, QRect, SIGNAL
from earley import Rule
import earley
import sys

def main():
    app = QtGui.QApplication(sys.argv)
    main = Main()
    main.show()
    sys.exit(app.exec_())

class Main(QtGui.QMainWindow):
    def __init__(self, parent = None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setWindowTitle("a little list editor")
        self.setGeometry(100, 100, 900, 300)
        #menu = self.menuBar()
        #test = menu.addMenu("Test")
        self.editor = CustomEditor(self)
        self.setCentralWidget(self.editor)

        #status = self.statusBar()
        #status.showMessage("XXX: implement statusbar")

class CustomEditor(QtGui.QFrame):
    def __init__(self, parent=None):
        QtGui.QFrame.__init__(self, parent)
        self.t_font = QtGui.QFont('Monospace', 5)
        self.t_fontht = QtGui.QFontMetrics(self.t_font).height() + 3
        self.t_fontwt = QtGui.QFontMetrics(self.t_font).width(" ")

        self.font = QtGui.QFont('Monospace', 9)
        self.fontht = QtGui.QFontMetrics(self.font).height() + 3
        self.fontwt = QtGui.QFontMetrics(self.font).width(" ")
        self.setCursor(QtCore.Qt.IBeamCursor)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.grammar = [
            Rule("file", ['expr-10']),
            Rule("file", ['file', 'expr-10']),
            Rule("expr-10", ['expr-10', 'plus', 'expr-20']),
            Rule("expr-10", ['expr-20']),
            Rule("expr-20", ['expr-20', 'star', 'term']),
            Rule("expr-20", ['term']),
            Rule("term", ['symbol']),
        ]

        self.root = GroupCell([
            TextCell("abrams"),
            TextCell("basic"),
            TextCell("cobol"),
            TextCell("delaynay"),
            TextCell("fortran"),
            TextCell("gotham"),
            #GroupCell([
            #    GroupCell([
            #        GroupCell([TextCell("banana"), TextCell("*"), TextCell("cello")], 'mul'),
            #        TextCell("+"),
            #        TextCell("elephone"),
            #    ], 'add'),
            #    TextCell("=="),
            #    GroupCell([TextCell('hieroglyph'), TextCell('idle')], 'call')
            #], "eq")
        ], "file")

        self.head = self.root.textcells([])[3].offset(0)
        self.tail = self.head
        self.parsePosition(self.head)

    def parsePosition(self, position):
        cell = position.cell.parent
        damaged = None
        while cell is not None:
            if cell.rule is None:
                damaged = cell
            cell = cell.parent
        if damaged is None:
            return
        parser = earley.parser(self.grammar, damaged.name)

        index = 0
        while index < len(damaged):
            scell = damaged[index]
            if isinstance(scell, TextCell):
                scell.name = 'symbol'
                if scell.text == '+':
                    scell.name = "plus"
                if scell.text == '*':
                    scell.name = "star"
            if scell.name not in parser.expect and isinstance(scell, TextCell):
                if len(parser.input) > 0 and not isinstance(parser.input[-1], TextCell):
                    index -= 1
                    parser.unstep()
                    damaged[index].collapse()
                    continue
                if damaged.parent is None:
                    return
                damaged.collapse()
                return self.parsePosition(position)
            if scell.name in parser.expect:
                parser.step(scell)
                index += 1
            else:
                scell.collapse()

        if not parser.accept:
            if damaged.parent is None:
                return
            damaged.collapse()
            return self.parsePosition(position)
        assert parser.accept
        roots = list(parser.roots)
        assert len(roots) == 1
        damaged[:] = []
        for root in roots:
            self.traverse(parser, root, 0, len(parser.input), damaged)

    def traverse(self, parser, rule, start, stop, cell):
        midresults = list(parser.chains(rule.rhs, start, stop))
        cell.name = unicode(rule.lhs)
        if len(midresults) > 1:
            cell.rule = None
            cell[:] = parser.input[start:stop]
            return
        for midresult in midresults:
            cell.rule = rule
            for nonleaf, rule, start, stop in midresult:
                if nonleaf:
                    subcell = GroupCell([])
                    cell.append(subcell)
                    self.traverse(parser, rule, start, stop, subcell)
                else:
                    cell.append(parser.input[start])

    def paintEvent(self, event):
        QtGui.QFrame.paintEvent(self, event)
        paint = QtGui.QPainter()
        paint.begin(self)
        paint.setFont(self.font)

        x = 10
        for cell in self.root.textcells([]):
            cell.x = x
            cell.y = 10
            cell.height = self.fontht
            cell.width = self.fontwt * len(cell.text)
            if cell.width == 0:
                cell.width = 5
                paint.drawRect(QRect(x-2, 10 - 3, 4, 2))
                paint.drawRect(QRect(x-2, 10 + self.fontht - 3, 4, 2))
                x += 5
            for c in cell.text:
                paint.drawText(QPointF(x, 10 + self.fontht*0.75), c)
                x += self.fontwt
            x += self.fontwt

        base = 5 + self.fontht*0.75 + self.root.maxdepth * 20
        
        for i, cell in self.root.depth_groupcells([], 0):
            left = cell.left_textcell
            right = cell.right_textcell
            cell.x = left.x
            cell.y = base - 20*i
            cell.height = 10
            cell.width = right.x + right.width - left.x
            self.draw_span(paint, left.x, right.x+right.width, cell.y, cell.name + ("" if cell.rule else " [+]"))

        x = self.head.cell.x + self.head.index * self.fontwt
        self.draw_cursor(paint, x, 10)
        if self.head != self.tail:
            x = self.tail.cell.x + self.tail.index * self.fontwt
            self.draw_cursor(paint, x, 10)

        paint.end()
        self.emit(SIGNAL("painted()"))

    def draw_span(self, paint, x0, x1, y, text):
        paint.setFont(self.t_font)
        w = x1-x0
        m = len(text) * self.t_fontwt
        n = (w-m)/2
        paint.drawRect(QRect(x0, y+5, n, 1))
        paint.drawRect(QRect(x1-n, y+5, n, 1))
        paint.drawRect(QRect(x0, y, 1, 10))
        paint.drawRect(QRect(x1, y, 1, 10))
        paint.drawText(QPointF(x0 + n, y + self.t_fontht*0.525), text)

    def draw_cursor(self, paint, x, y):
        pen = paint.pen()
        colorhex = self.palette().color(QPalette.Text)
        pen.setColor(QColor(colorhex))
        paint.setPen(pen)
        draw_cursor_at = QRect(x, y, 0, self.fontht - 3)
        paint.drawRect(draw_cursor_at)

    def reset(self):
        self.update()

    def focusNextPrevChild(self, b):
        return False

    def mousePressEvent(self, e):
        self.update()

    def mouseMoveEvent(self, e):
        self.update()

    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_Escape:
            sys.exit(0)
        elif e.key() == QtCore.Qt.Key_Tab:
            self.parsePosition(self.head)
        elif e.key() == QtCore.Qt.Key_Up:
            print 'XXX: ambiguity-list up'
        elif e.key() == QtCore.Qt.Key_Down:
            print 'XXX: ambiguity-list down'
        elif e.key() == QtCore.Qt.Key_Delete:
            if self.head == self.tail:
                _, self.head = self.head.collapse(self.head + 1)
            else:
                _, self.head = self.head.collapse(self.tail)
            self.tail = self.head
            self.parsePosition(self.head)
        elif e.key() == QtCore.Qt.Key_Backspace:
            if self.head == self.tail:
                _, self.head = self.head.collapse(self.head - 1)
            else:
                _, self.head = self.head.collapse(self.tail)
            self.tail = self.head
            self.parsePosition(self.head)
        elif e.key() == QtCore.Qt.Key_Space:
            if self.head != self.tail:
                _, self.head = self.head.collapse(self.tail)
            if not e.modifiers() & QtCore.Qt.ShiftModifier:
                _, self.head = self.head.split()
            else:
                self.head, _ = self.head.split()
            self.tail = self.head
            self.parsePosition(self.head)
        elif e.key() == QtCore.Qt.Key_Left:
            self.head = self.head - 1
            if not e.modifiers() & QtCore.Qt.ShiftModifier:
                self.tail = self.head
        elif e.key() == QtCore.Qt.Key_Right:
            self.head = self.head + 1
            if not e.modifiers() & QtCore.Qt.ShiftModifier:
                self.tail = self.head
        else:
            _, self.head = self.head.put(e.text())
            self.tail = self.head
            self.parsePosition(self.head)
        self.update()
        return QtGui.QFrame.keyPressEvent(self, e)
#
#    def draw_selection(self, paint, draw_selection_start, draw_selection_end):
#        x1, y1, line1 = draw_selection_start
#        x2, y2, line2 = draw_selection_end
#        if y1 == y2:
#            paint.fillRect(QRectF(x1, 3 + y1 * self.fontht, x2-x1, self.fontht), QColor(0,0,255,100))
#        else:
#            paint.fillRect(QRectF(x1, 3 + y1 * self.fontht, self.tm.lines[line1].width*self.fontwt - x1, self.fontht), QColor(0,0,255,100))
#            y = y1 + self.tm.lines[line1].height
#            for i in range(line1+1, line2):
#                paint.fillRect(QRectF(0, 3 + y * self.fontht, self.tm.lines[i].width*self.fontwt, self.fontht), QColor(0,0,255,100))
#                y = y + self.tm.lines[i].height
#            paint.fillRect(QRectF(0, 3 + y2 * self.fontht, x2, self.fontht), QColor(0,0,255,100))

class Position(object):
    def __init__(self, cell, index):
        self.cell = cell
        self.index = index

    def __add__(self, offset):
        return self.cell.offset(self.index + offset)

    def __sub__(self, offset):
        return self.cell.offset(self.index - offset)

    def collapse(self, other):
        if self.cell is other.cell and self.index == other.index:
            return u"", self
        if self.cell is other.cell:
            start = min(self.index, other.index)
            stop = max(self.index, other.index)
            drop = self.cell.text[start:stop]
            self.cell.text = self.cell.text[:start] + self.cell.text[stop:]
            if self.cell.parent is not None:
                self.cell.parent.rule = None 
            return drop, Position(self.cell, start)
        common = self.cell.common(other.cell)
        while self.cell.parent != common:
            self.cell.parent.collapse()
        while other.cell.parent != common:
            other.cell.parent.collapse()
        si = common.index(self.cell)
        oi = common.index(other.cell)
        if si > oi:
            si, oi = oi, si
            self, other = other, self
        s = [TextCell(self.cell.text[self.index:])]
        o = [TextCell(other.cell.text[:other.index])]
        m = TextCell(self.cell.text[:self.index] + other.cell.text[other.index:])
        drop = s + common[si+1:oi] + o
        common[si:oi+1] = [m]
        common.rule = None 
        return drop, m.offset(self.index)

    def split(self):
        return self.cell.split(self.index)

    def put(self, text):
        cell, index = self.cell, self.index
        cell.text = cell.text[:index] + text + cell.text[index:]
        if cell.parent is not None:
            cell.parent.rule = None 
        return self, Position(cell, index + len(text))

    def __eq__(self, other):
        return (isinstance(other, Position)
            and self.cell is other.cell
            and self.index == other.index)

class Cell(object):
    x = 0
    y = 0
    width = 0
    height = 0
    parent = None

    @property
    def root(self):
        root = self
        while root.parent is not None:
            root = root.parent
        return root

    @property
    def depth(self):
        depth = 0
        while self.parent is not None:
            self = self.parent
            depth += 1
        return depth

    @property
    def before(self):
        while self.parent is not None:
            for cell in reversed(self.parent[:self.parent.index(self)]):
                yield cell
            self = self.parent

    @property
    def after(self):
        while self.parent is not None:
            for cell in self.parent[self.parent.index(self)+1:]:
                yield cell
            self = self.parent

    def common(x1, x2):
        if x1 is x2:
            return x1
        d1 = x1.depth
        d2 = x2.depth
        mind = min(d1, d2)
        for d in range(mind, d1):
            x1 = x1.parent
        for d in range(mind, d2):
            x2 = x2.parent
        while x1 != x2:
            x1 = x1.parent
            x2 = x2.parent
        return x1

class GroupCell(Cell):
    def __init__(self, contents, name="", rule=None):
        self.contents = contents
        self.name = name
        for cell in contents:
            cell.parent = self
        self.rule = rule

    def __getitem__(self, index):
        return self.contents[index]

    def __setitem__(self, index, value):
        dropped = self.contents[index]
        for cell in dropped if isinstance(index, slice) else [dropped]:
            cell.parent = None
        self.contents[index] = value
        for cell in value if isinstance(index, slice) else [value]:
            cell.parent = self

    def __len__(self):
        return len(self.contents)

    def append(self, cell):
        self.contents.append(cell)
        cell.parent = self

    def index(self, cell):
        return self.contents.index(cell)

    @property
    def left_textcell(self):
        for cell in self.contents:
            cell = cell.left_textcell
            if cell is not None:
                return cell

    @property
    def right_textcell(self):
        for cell in reversed(self.contents):
            cell = cell.right_textcell
            if cell is not None:
                return cell

    @property
    def maxdepth(self):
        if len(self.contents) == 0:
            return 0
        return max(cell.maxdepth for cell in self.contents) + 1

    def depth_groupcells(self, out, depth):
        out.append((depth, self))
        for cell in self.contents:
            cell.depth_groupcells(out, depth+1)
        return out

    def textcells(self, out):
        for node in self.contents:
            node.textcells(out)
        return out

    @property
    def prev_textcell(self):
        if self.parent is None:
            return None

    @property
    def next_textcell(self):
        if self.parent is None:
            return None

    def collapse(self):
        parent = self.parent
        index = parent.index(self)
        parent[index:index+1] = self.contents
        self.contents = []
        parent.rule = None 

class TextCell(Cell):
    def __init__(self, text=u""):
        self.text = text
        self.name = "symbol"

    @property
    def left_textcell(self):
        return self

    @property
    def right_textcell(self):
        return self

    @property
    def maxdepth(self):
        return 0

    def textcells(self, out):
        out.append(self)
        return out

    def depth_groupcells(self, out, depth):
        return out

    @property
    def prev_textcell(self):
        for cell in self.before:
            cell = cell.right_textcell
            if cell is not None:
                return cell

    @property
    def next_textcell(self):
        for cell in self.after:
            cell = cell.left_textcell
            if cell is not None:
                return cell

    def offset(self, index):
        L = len(self.text)
        if index < 0:
            cell = self.prev_textcell
            if cell is None:
                return Position(self, 0)
            else:
                return cell.offset(index + len(cell.text) + 1)
        if index > L:
            cell = self.next_textcell
            if cell is None:
                return Position(self, L)
            else:
                return cell.offset(index - L - 1)
        return Position(self, index)

    def split(self, index):
        i = self.parent.index(self)
        self.parent.rule = None 
        self.parent[i:i+1] = a, b = TextCell(self.text[:index]), TextCell(self.text[index:])
        return Position(a, len(a.text)), Position(b, 0)

if __name__ == "__main__":
    main()
