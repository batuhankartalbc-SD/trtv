"""Arayüz bileşeni regresyonları (ekransız Qt)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_toggle_animation_does_not_move_widget():
    """Regresyon: animasyon özelliği 'pos' adındayken anahtar panelin sol üstüne kayıyordu."""
    from PySide6.QtCore import QCoreApplication, QElapsedTimer
    from PySide6.QtWidgets import QApplication, QGridLayout, QLabel, QWidget
    from trceviri.widgets import Toggle
    app = QApplication.instance() or QApplication([])
    w = QWidget(); g = QGridLayout(w)
    g.addWidget(QLabel("Başlık"), 0, 0); g.addWidget(QLabel("Etkin"), 1, 0)
    t = Toggle(True); g.addWidget(t, 1, 1)
    w.resize(400, 200); w.show(); app.processEvents()
    before = t.pos()
    assert before.y() > 0
    t.setChecked(False)
    timer = QElapsedTimer(); timer.start()
    while timer.elapsed() < 400:
        QCoreApplication.processEvents()
    assert t.pos() == before
    assert t.getPos() == 0.0
    w.close()
