from PyQt5 import QtWidgets
from ui_main import Ui_Form
from ui.basic_info_page import BasicInfoPage


class MainWindow(QtWidgets.QMainWindow, Ui_Form):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        
        # 初始化数据模型
        self.bid_data = BidData()
        
        # 按钮重命名和信号连接
        self.btn_step1 = self.btn_step1
        self.btn_step2 = self.btn_step2
        self.btn_step3 = self.btn_step3
        self.btn_step4 = self.btn_step4
        
        # 配置步骤导航
        self.steps = {
            0: (self.btn_step1, BasicInfoPage),
          #  1: (self.btn_step2, OutlinePage),
           # 2: (self.btn_step3, ContentPage),
           # 3: (self.btn_step4, ExportPage)
        }
        
        # 初始化页面
        self.init_pages()
        
    def init_pages(self):
        """初始化所有步骤页面"""
        #self.stackedWidget.clear()
        self.stackedWidget.addWidget(BasicInfoPage(self.bid_data))
        for idx in self.steps.values():
            page = idx[1](self.bid_data)
            self.stackedWidget.addWidget(page)
            
        # 连接按钮点击事件
        self.btn_step1.clicked.connect(lambda: self.switch_page(0))
        self.btn_step2.clicked.connect(lambda: self.switch_page(1))
        self.btn_step3.clicked.connect(lambda: self.switch_page(2))
        self.btn_step4.clicked.connect(lambda: self.switch_page(3))

    def update_right_panel(self):
        """更新右侧项目概览"""
        info = self.bid_data.info
        self.lbl_project_name.setText(info.project_name)
        self.lbl_project_code.setText(info.project_code)
        self.lbl_bidder.setText(info.bidder)
    
    def switch_page(self, index):
        """切换步骤页面"""
        self.stackedWidget.setCurrentIndex(index)
        self.update_sidebar_style(index)
    
    def update_sidebar_style(self, active_index):
        """更新导航按钮样式"""
        for idx, (btn, _) in self.steps.items():
            if idx == active_index:
                btn.setStyleSheet("background: #e0f0ff;")
            else:
                btn.setStyleSheet("")

if __name__ == "__main__":
    import sys
    from core.data_model import BidData  # 确保导入BidData
    
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
