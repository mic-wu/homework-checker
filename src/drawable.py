from PyQt5.QtCore import Qt, QPoint, QRect
from PyQt5.QtGui import QPen


def nextDirection(r):
    dirs = {"west": "north", "north": "east", "east": "south", "south": "west"}
    return dirs[r]

def fallBackDirection(r, available):
    # todo: Refactor LMAO
    fallbacks = {
        "west": ["west", "horizontal", "all"],
        "north": ["north", "vertical", "all"],
        "east": ["east", "horizontal", "all"],
        "south": ["south", "vertical", "all"]
    }
    for f in fallbacks[r]:
        if f in available:
            return f
    raise ValueError(f"No fallback direction available for {r}. This should never happen.")

def getForDir(r, mapping):
    theDir = fallBackDirection(r, mapping.keys())
    return mapping[theDir]

########################################################### 

class Port():
    def __init__(self, name, pos, direction):
        self.name = name
        self.pos = pos
        self.direction = direction

class TextField():
    def __init__(self, id, rect, align, fmt):
        self.id = id
        self.rect = rect
        self.align = align
        self.format = fmt

class Drawable():
    def __init__(self):
        pass

    def in_bounds(self, pos):
        '''
        Returns True if the given position is within the bounds of the drawable.
        '''
        raise NotImplementedError
    
    def in_text_bounds(self, pos):
        '''
        If the given position is within the bounds of some text within the drawable,
        return the id of the text. Otherwise, return None.
        '''
        raise NotImplementedError

    def _set_pen(self, painter, is_ghost, is_hovered, is_selected):
        penColor = Qt.blue if is_selected else Qt.black
        painter.setPen(QPen(penColor, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        
        if is_ghost:
            painter.setOpacity(0.3)
        elif is_hovered:
            painter.setOpacity(0.5)
        else:
            painter.setOpacity(1.0)

    def getPorts(self):
        raise NotImplementedError

    def draw(self, painter, is_ghost=False, is_hovered=False, is_selected=False, textHovered=None):
        raise NotImplementedError

###########################################################

class Wire(Drawable):
    def __init__(self, id, start, end):
        super().__init__()
        self.id = id
        self.start = start
        self.end = end

    def getPorts(self):
        return (Port("start", self.start, "none"), Port("end", self.end, "none"))
    
    def getDirection(self):
        if self.start.x() == self.end.x():
            return "vertical"
        elif self.start.y() == self.end.y():
            return "horizontal"
        else:
            raise ValueError("Wire is not horizontal or vertical.")

    def in_bounds(self, pos):
        margin = 6
        topLeft = QPoint(min(self.start.x(), self.end.x()) - margin, min(self.start.y(), self.end.y()) - margin)
        bottomRight = QPoint(max(self.start.x(), self.end.x()) + margin, max(self.start.y(), self.end.y()) + margin)
        return QRect(topLeft, bottomRight).contains(pos)
    
    def in_text_bounds(self, pos):
        return None

    def draw(self, painter, is_ghost=False, is_hovered=False, is_selected=False, textHovered=None):
        self._set_pen(painter, is_ghost, is_hovered, is_selected)
        painter.drawLine(self.start, self.end)

    @staticmethod
    def drawWireCursor(painter, mousePos):
        size = 8
        painter.setPen(QPen(Qt.black, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setOpacity(0.5)
        painter.drawLine(mousePos + QPoint(-size, 0), mousePos + QPoint(size, 0))
        painter.drawLine(mousePos + QPoint(0, -size), mousePos + QPoint(0, size))

###########################################################

class Component(Drawable):
    symbol = "-"
    ports = {
        "all": []
    }
    boundingBox = {
        "all": QRect()
    }
    textFields = {
        "all": []
    }

    def __init__(self, id, pos, r):
        super().__init__()
        self.pos = pos
        self.id = id
        self.r = r

    def getPorts(self):
        return [Port(port.name, port.pos + self.pos, port.direction) for port in getForDir(self.r, self.ports)]

    def in_bounds(self, pos):
        return getForDir(self.r, self.boundingBox).contains(pos - self.pos)
    
    def in_text_bounds(self, pos):
        for textField in getForDir(self.r, self.textFields):
            if textField.rect.translated(self.pos).contains(pos):
                return textField.id
    
    def set_pos(self, pos):
        self.pos = pos
    def set_r(self, r):
        self.r = r

    def _drawTextFields(self, painter, textHovered=None):
        for textField in getForDir(self.r, self.textFields):
            painter.setOpacity(0.5 if textField.id == textHovered else 1.0)
            painter.drawText(textField.rect.translated(self.pos), textField.align, textField.format.format(getattr(self, textField.id)))

###########################################################

class Resistor(Component):
    symbol = "R"
    ports = {
        "horizontal": [Port("p1", QPoint(-40,0), "east"), Port("p2", QPoint(40,0), "west")],
        "vertical": [Port("p1", QPoint(0,-40), "south"), Port("p2", QPoint(0,40), "north")]
    }
    boundingBox = {
        "horizontal": QRect(-42, -12, 84, 24),
        "vertical": QRect(-12, -42, 24, 84),
    }
    textFields = {
        "horizontal": [TextField("resistance", QRect(-30, 12, 60, 20), Qt.AlignCenter, "{}Ω")],
        "vertical": [TextField("resistance", QRect(15, -10, 60, 20), Qt.AlignLeft, "{}Ω")]
    }

    def __init__(self, id, pos, r, resistance="1k"):
        super().__init__(id, pos, r)
        self.resistance = resistance

    def draw(self, painter, is_ghost=False, is_hovered=False, is_selected=False, textHovered=None):
        self._set_pen(painter, is_ghost, is_hovered, is_selected)

        offsets = [(-40,0), (-30,0), (-25,-10), (-15,10), (-5,-10), (5,10), (15,-10), (25,10), (30,0), (40,0)]
        if self.r == "north" or self.r == "south":
            offsets = [(y, x) for x, y in offsets]
    
        points = [self.pos+QPoint(x,y) for x, y in offsets]
        painter.drawPolyline(points)

        self._drawTextFields(painter, textHovered)

###########################################################

class Capacitor(Component):
    symbol = "C"
    ports = {
        "horizontal": [Port("p1", QPoint(-40,0), "east"), Port("p2", QPoint(40,0), "west")],
        "vertical": [Port("p1", QPoint(0,-40), "south"), Port("p2", QPoint(0,40), "north")]
    }
    boundingBox = {
        "horizontal": QRect(-42, -22, 84, 44),
        "vertical": QRect(-22, -42, 44, 84),
    }
    textFields = {
        "horizontal": [TextField("capacitance", QRect(-30, 22, 60, 20), Qt.AlignCenter, "{}F")],
        "vertical": [TextField("capacitance", QRect(24, -10, 60, 20), Qt.AlignLeft, "{}F")]
    }

    def __init__(self, id, pos, r, capacitance="1u"):
        super().__init__(id, pos, r)
        self.capacitance = capacitance

    def draw(self, painter, is_ghost=False, is_hovered=False, is_selected=False, textHovered=None):
        self._set_pen(painter, is_ghost, is_hovered, is_selected)

        lines = [ [(-40,0), (-8,0)], [(-8,-20), (-8,20)], [(8,-20), (8,20)], [(8,0), (40,0)] ]
        if self.r == "north" or self.r == "south":
            lines = [[(y, x) for x, y in line] for line in lines]
            
        for line in lines:
            points = [self.pos+QPoint(x,y) for x, y in line]
            painter.drawPolyline(points)

        self._drawTextFields(painter, textHovered)

###########################################################

class VoltageSource(Component):
    symbol = "V"
    ports = {
        "horizontal": [Port("p1", QPoint(-40,0), "east"), Port("p2", QPoint(40,0), "west")],
        "vertical": [Port("p1", QPoint(0,-40), "south"), Port("p2", QPoint(0,40), "north")]
    }
    boundingBox = {
        "horizontal": QRect(-42, -22, 84, 44),
        "vertical": QRect(-22, -42, 44, 84),
    }
    textFields = {
        "horizontal": [TextField("voltage", QRect(-30, 22, 60, 20), Qt.AlignCenter, "{}V")],
        "vertical": [TextField("voltage", QRect(24, -10, 60, 20), Qt.AlignLeft, "{}V")]
    }

    def __init__(self, id, pos, r, voltage="5"):
        super().__init__(id, pos, r)
        self.voltage = voltage

    def draw(self, painter, is_ghost=False, is_hovered=False, is_selected=False, textHovered=None):
        self._set_pen(painter, is_ghost, is_hovered, is_selected)

        # default is east
        lines = [ [(-40,0), (-15,0)], [(-15,-12), (-15,12)], [(-5,-20), (-5,20)], [(5,-12), (5,12)], [(15,-20), (15,20)], [(15,0), (40,0)] ]

        if self.r == "north":
            lines = [[(-y, -x) for x, y in line] for line in lines]
        elif self.r == "west":
            lines = [[(-x, y) for x, y in line] for line in lines]
        elif self.r == "south":
            lines = [[(-y, x) for x, y in line] for line in lines]
            
        for line in lines:
            points = [self.pos+QPoint(x,y) for x, y in line]
            painter.drawPolyline(points)

        self._drawTextFields(painter, textHovered)

class Ground(Component):
    symbol = "GND"
    ports = {
        "west": [Port("p1", QPoint(0,0), "east")],
        "north": [Port("p1", QPoint(0,0), "south")],
        "east": [Port("p1", QPoint(0,0), "west")],
        "south": [Port("p1", QPoint(0,0), "north")]
    }
    boundingBox = {
        "west": QRect(-2, -22, 44, 44),
        "north": QRect(-22, -2, 44, 44),
        "east": QRect(-42, -22, 44, 44),
        "south": QRect(-22, -42, 44, 44),
    }
    textFields = {
        "all": [],
    }

    def draw(self, painter, is_ghost=False, is_hovered=False, is_selected=False, textHovered=None):
        self._set_pen(painter, is_ghost, is_hovered, is_selected)

        # default is east
        lines = [[(-20, 0), (0,0)], [(-20, -15), (-20, 15)], [(-27, -10), (-27, 10)], [(-34, -5), (-34, 5)]]

        if self.r == "north":
            lines = [[(-y, -x) for x, y in line] for line in lines]
        elif self.r == "west":
            lines = [[(-x, y) for x, y in line] for line in lines]
        elif self.r == "south":
            lines = [[(-y, x) for x, y in line] for line in lines]
            
        for line in lines:
            points = [self.pos+QPoint(x,y) for x, y in line]
            painter.drawPolyline(points)

        self._drawTextFields(painter, textHovered)