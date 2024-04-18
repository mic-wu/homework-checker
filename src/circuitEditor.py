import copy

from PyQt5.QtWidgets import QWidget, QInputDialog
from PyQt5.QtGui import QMouseEvent, QPaintEvent, QPixmap, QPainter, QShowEvent
from PyQt5.QtCore import Qt, QPoint, QTimer, QElapsedTimer, QPointF

from drawable import Resistor, Capacitor, VoltageSource, Wire, Ground, nextDirection

class CircuitEditor(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # intialize a timer that will be used to update the scene
        
        self.elapsedTimer = QElapsedTimer()
        self.elapsedTimer.start()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animateTick)
        self.lastTime = self.elapsedTimer.elapsed()
        self.timer.start()

        # set focus policy to accept key events
        self.setFocusPolicy(Qt.StrongFocus)

        # fill the entire parent
        self.setMouseTracking(True)
        self.prev_raw_mouse_pos = QPoint(0, 0)
        self.raw_mouse_pos = QPoint(0, 0)
        self.mouse_pos = QPoint(0, 0)
        self.mouse_grid_pos = QPoint(0, 0)

        self.mouse_down = False

        self.hoveredItemId = None
        self.selectionId = None
        
        self.mode = "place" # place, edit, wire

        self.items = [Resistor("R1", QPoint(0, 0), "west")]
        self.wires = []

        self.toPlace = Resistor("R2", QPoint(0, 0), "west")
        self.ghostPos = QPointF(0, 0)
        self.toPlaceR = "west"
        self.lastTypingTime = 0

        self.wireStart = None
        self.movedWire = False
        self.ghostWires = []

        self.pan = QPoint(0, 0)
        self.zoom = 0.0
        self.zoomValue = 1.0

    def _getNow(self):
        return self.elapsedTimer.elapsed()

    def _animateTick(self):
        now = self._getNow()
        dtMs = now - self.lastTime
        self.lastTime = now

        snapped_pos = (self.mouse_pos) / 20 * 20
        self.ghostPos += (snapped_pos - self.ghostPos) * (1 - 0.1 ** (dtMs / 100))

        if self.mode == "wire" and self.wireStart is not None:
            self._computeGhostWire(self.ghostPos)

        self.update()

    def _updateMousePos(self, event: QMouseEvent):
        self.prev_raw_mouse_pos = self.raw_mouse_pos
        self.raw_mouse_pos = event.pos()

        # nasty math to update mouse pos
        self.mouse_pos = ((self.raw_mouse_pos - QPoint(self.width()//2, self.height()//2)) / self.zoomValue + self.pan)

        old_grid_pos = self.mouse_grid_pos
        self.mouse_grid_pos = self.mouse_pos / 20 * 20

        res = self._hoveredTextId()
        if res is not None:
            item, hoveredTextId = res
            self.hoveredItemId = f"{item.id}:{hoveredTextId}"
        else:
            self.hoveredItemId = self._hoveredItemId()

        if old_grid_pos != self.mouse_grid_pos:
            if self.mode == "wire" and self.wireStart is not None:
                self.movedWire = True

        return old_grid_pos != self.mouse_grid_pos

    def _nextComponentID(self, prefix):
        idNum = 1
        while True:
            id = f"{prefix}{idNum}"
            if not any(item.id == id for item in self.items):
                break
            idNum += 1
        return id

    def _placeItem(self):
        snapped_pos = (self.mouse_pos) / 20 * 20

        # placing an item resets typing cooldown
        self.lastTypingTime = 0

        if self._alreadyItemAt(snapped_pos):
            return

        new_item = copy.deepcopy(self.toPlace)
        new_item.set_pos(snapped_pos)
        new_item.set_r(self.toPlaceR)

        # generate a unique id

        self.items.append(new_item)
        self.toPlace.id = self._nextComponentID(self.toPlace.symbol)
        self.update()

    def _placeWire(self):
        self._computeGhostWire(self.mouse_grid_pos)
        for wire in self.ghostWires:
            idNum = 1
            while True:
                id = f"wire{idNum}"
                if not any(wire.id == id for wire in self.wires):
                    break
                idNum += 1
            wire.id = id
            self.wires.append(wire)
        self.wireStart = None
        self.ghostWires = []

    def _hoveredItemId(self):
        for wire in self.wires:
            if wire.in_bounds(self.mouse_pos):
                return wire.id
        for item in self.items:
            if item.in_bounds(self.mouse_pos):
                return item.id
        return None

    def _hoveredTextId(self):
        for item in self.items:
            textId = item.in_text_bounds(self.mouse_pos)
            if textId is not None:
                return (item, textId)
        return None

    def _drawGhost(self, painter):
        self.toPlace.set_pos(self.ghostPos.toPoint())
        self.toPlace.set_r(self.toPlaceR)
        self.toPlace.draw(painter, is_ghost=True)

    def _drawGhostWire(self, painter):
        if self.wireStart is None:
            Wire.drawWireCursor(painter, self.mouse_grid_pos)
        for wire in self.ghostWires:
            wire.draw(painter, is_ghost=True)

    def _computeGhostWire(self, endPos):
        if self.wireStart is None:
            return
        
        snapped_pos = endPos

        # if its a QPointF, convert it to QPoint
        if isinstance(snapped_pos, QPointF):
            snapped_pos = snapped_pos.toPoint()

        offset = snapped_pos - self.wireStart

        if offset == QPoint(0, 0):
            self.ghostWires = []
            return

        if abs(offset.x()) > abs(offset.y()):
            latVal = lambda p: p.x()
            ortVal = lambda p: p.y()
            setOrthogonal = lambda p, v: p.setY(v)
            dirs = ["west", "east"] if offset.x() > 0 else ["east", "west"]
        else:
            latVal = lambda p: p.y()
            ortVal = lambda p: p.x()
            setOrthogonal = lambda p, v: p.setX(v)
            dirs = ["north", "south"] if offset.y() > 0 else ["south", "north"]

        setOrthogonal(snapped_pos, ortVal(self.wireStart))

        bounds = sorted([latVal(self.wireStart), latVal(snapped_pos)])

        allPorts = self._allPorts()
        portsOfInterest = [port for port in allPorts if ortVal(port.pos) == ortVal(self.wireStart) and bounds[0] <= latVal(port.pos) <= bounds[1]]

        isPosDir = latVal(offset) > 0
        portsOfInterest.sort(key=lambda port: latVal(port.pos) * (1 if isPosDir else -1) + (0.1 if port.direction == dirs[1] else 0)) # iffy

        ghostWires = []
        isWire = True
        lastPoint = self.wireStart

        for port in portsOfInterest:
            if isWire and lastPoint != port.pos:
                ghostWires.append(Wire("ghost", lastPoint, port.pos))
            if port.direction == dirs[1]:
                isWire = False
            elif port.direction == dirs[0]:
                isWire = True
            lastPoint = port.pos
        
        if isWire and lastPoint != snapped_pos:
            ghostWires.append(Wire("ghost", lastPoint, snapped_pos))

        self.ghostWires = ghostWires


    def _alreadyItemAt(self, pos):
        for item in self.items:
            if item.pos == pos:
                return True
        return False
    
    def _allPorts(self):
        ports = []
        for item in self.items:
            ports += item.getPorts()
        for wire in self.wires:
            ports += wire.getPorts()
        return ports

    def mousePressEvent(self, event: QMouseEvent):
        self._updateMousePos(event)
        shifted = (event.modifiers() & Qt.ShiftModifier) == Qt.ShiftModifier

        if shifted:
            pass
        else:
            if not self.mouse_down:
                if self.mode == "place":
                    self._placeItem()
                elif self.mode == "wire":
                    if self.wireStart is None:
                        self.wireStart = self.mouse_grid_pos
                        self.movedWire = False
                    else:
                        self._placeWire()
                elif self.mode == "edit":
                    if self.hoveredItemId is not None and self.hoveredItemId.find(":") != -1:
                        # edit the value
                        itemId, textId = self.hoveredItemId.split(":")

                        # open a dialog to edit the value
                        qstr, ok = QInputDialog.getText(self, "Edit Value", "Enter the new value:")
                        if ok:
                            for item in self.items:
                                if item.id == itemId:
                                    item.__setattr__(textId, qstr)
                    else:
                        self.selectionId = self.hoveredItemId
                    # if self.hoveredItemId is not None:


        self.mouse_down = True
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        self._updateMousePos(event)

        # drag logic
        if self.mouse_down and (event.modifiers() & Qt.ShiftModifier):
            self.pan = self.pan - (self.raw_mouse_pos - self.prev_raw_mouse_pos)

        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.mouse_down = False

        if self.mode == "wire" and self.wireStart is not None:
            if self.movedWire:
                self._placeWire()

        self.update()

    def wheelEvent(self,event):
        self.zoom += event.angleDelta().y() / 120
        self.zoomValue = 1.1 ** self.zoom
        self._updateMousePos(event)
        self.update()
    
    def keyPressEvent(self, event):
        super().keyPressEvent(event)

        shiftKey = (event.modifiers() & Qt.ShiftModifier) == Qt.ShiftModifier

        if event.isAutoRepeat():
            return
        
        if event.key() == Qt.Key.Key_Escape:
            if self.mode == "wire" and self.wireStart is not None:
                self.wireStart = None
                self.ghostWires = []
            elif self.selectionId is not None:
                self.selectionId = None
            else:
                self.mode = "edit"
        elif event.key() == Qt.Key.Key_R and not shiftKey:
            self.toPlaceR = nextDirection(self.toPlaceR)
        elif event.key() == Qt.Key.Key_W and shiftKey:
            self.mode = "wire"
        elif event.key() == Qt.Key.Key_R and shiftKey:
            # resistor
            self.mode = "place"
            self.toPlace = Resistor(self._nextComponentID("R"), QPoint(0, 0), "west")
        elif event.key() == Qt.Key.Key_C and shiftKey:
            # capacitor
            self.mode = "place"
            self.toPlace = Capacitor(self._nextComponentID("C"), QPoint(0, 0), "west")
        elif event.key() == Qt.Key.Key_V and shiftKey:
            # voltage source
            self.mode = "place"
            self.toPlace = VoltageSource(self._nextComponentID("V"), QPoint(0, 0), "west")
        elif event.key() == Qt.Key.Key_G and shiftKey:
            # ground
            self.mode = "place"
            self.toPlace = Ground(self._nextComponentID("G"), QPoint(0, 0), "west")
        elif event.key() == Qt.Key.Key_Backspace or event.key() == Qt.Key.Key_X:
            if self.selectionId is not None:
                if self.selectionId.startswith("wire"):
                    self.wires = [wire for wire in self.wires if wire.id != self.selectionId]
                else:
                    self.items = [item for item in self.items if item.id != self.selectionId]
                self.selectionId = None
        
        if event.key() == Qt.Key.Key_Backspace:
            if self.mode == "place":
                self.toPlace.setPrimaryField("")
        else:
            if self.mode == "place":
                if len(event.text()) == 1 and "0123456789numkMG".find(event.text()) != -1:
                    v = ""
                    if self._getNow() - self.lastTypingTime < 500:
                        v = self.toPlace.getPrimaryField()
                    v += event.text()
                    self.toPlace.setPrimaryField(v)
                    self.lastTypingTime = self._getNow()
        
        self.update()


            

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter()
        painter.begin(self)
        painter.setPen(Qt.black)

        # viewport transformation
        painter.translate(self.width()/2, self.height()/2)
        painter.scale(self.zoomValue, self.zoomValue)
        painter.translate(-self.pan)

        # draw ghost
        if self.mode == "place":
            dist = (self.ghostPos - self.mouse_grid_pos).manhattanLength()
            if dist > 2 or not self._alreadyItemAt(self.mouse_grid_pos):
                self._drawGhost(painter)
        elif self.mode == "wire":
            if self.wireStart is not None:
                self._drawGhostWire(painter)
            Wire.drawWireCursor(painter, self.ghostPos)
        

        # draw wires
        for wire in self.wires:
            hovered = wire.id == self.hoveredItemId and self.mode == "edit"
            selected = wire.id == self.selectionId
            wire.draw(painter, is_hovered=hovered, is_selected=selected)

        # draw components
        for item in self.items:
            hovered = item.id == self.hoveredItemId and self.mode == "edit"
            
            textHovered = None
            if self.hoveredItemId is not None and self.hoveredItemId.find(":") != -1:
                itemId, textId = self.hoveredItemId.split(":")
                if item.id == itemId:
                    textHovered = textId

            selected = item.id == self.selectionId
            item.draw(painter, is_hovered=hovered, is_selected=selected, textHovered=textHovered)

        # draw UI stuff
        painter.resetTransform()
        painter.setPen(Qt.black)

        # mode
        painter.drawText(10, 20, self.mode)
        painter.drawText(10, 40, f"{self.mouse_pos.x()}, {self.mouse_pos.y()}")
        painter.drawText(10, 60, self.hoveredItemId)
    
        painter.end()
