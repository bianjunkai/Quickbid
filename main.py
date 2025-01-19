import sys
from PyQt5.QtWidgets import QApplication
from ui.mainwindow import MainWindow
from database.mongo import init_db

def main():
    app = QApplication(sys.argv)
    
    # 初始化数据库连接
    init_db()
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
