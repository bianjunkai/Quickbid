from PyQt5 import QtWidgets
from ui_main import Ui_Form
from ui.basic_info_page import BasicInfoPage
from ui.OutlinePage import OutlinePage
from core.data_model import BidData


class MainWindow(QtWidgets.QMainWindow, Ui_Form):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        
        # 初始化数据模型
        self.bid_data = BidData()
        self.current_step = 0 
        
        # 按钮重命名和信号连接
        #self.btn_step1 = self.btn_step1
        #self.btn_step2 = self.btn_step2
        #self.btn_step3 = self.btn_step3
        #self.btn_step4 = self.btn_step4

        # 连接按钮点击事件
        self.pushButton_9.clicked.connect(self.on_save_clicked)
        self.btn_step1.clicked.connect(lambda: self.switch_page(0))  # 基本信息
        self.btn_step2.clicked.connect(lambda: self.switch_page(1))  # 目录设计
        
        # 配置步骤导航
        self.steps = {
            0: (self.btn_step1, BasicInfoPage),
            1: (self.btn_step2, OutlinePage)
        }
        
        # 初始化页面
        self.init_pages()
        


    def init_pages(self):
        """初始化步骤页面"""
        self.pages = [
            BasicInfoPage(self.bid_data),
            OutlinePage(self.bid_data),
            #ContentPage(self.bid_data),
            #ExportPage(self.bid_data)
        ]
        
        for page in self.pages:
            self.stackedWidget.addWidget(page)

    def update_right_panel(self):
        """更新右侧信息展示"""
        # 项目概览
        info = self.bid_data.info
        self.label_project_name.setText(f"项目名称：{info.project_name}")
        self.label_project_code.setText(f"项目编号：{info.project_code}")
        # self.label_bidder_credit_code.setText(f"统一信用代码：{info.bidder_credit_code}")
        # 其他信息...
        
        # 实时更新按钮状态
        self.pushButton_9.setEnabled(self.current_step < 3)  # 最后一步禁用保存
        
    def switch_page(self, index):
        """切换步骤页面"""
        if 0 <= index < len(self.pages):
            self.stackedWidget.setCurrentIndex(index)
            self.update_nav_style(index)
            self.update_sidebar_style(index)

    def update_nav_style(self, active_index):
        """更新导航按钮样式"""
        buttons = [
            self.btn_step1,  # 基本信息按钮
            self.btn_step2,  # 目录设计按钮
        #    self.pushButton_4,  # 内容生成按钮
        #    self.pushButton_2   # 导出按钮
        ]
        
        for idx, btn in enumerate(buttons):
            btn.setStyleSheet("""
                QPushButton { 
                    background: %s; 
                    text-align: left; 
                    padding: 8px 
                }
            """ % ("#e0f0ff" if idx == active_index else "white"))
    
    def update_sidebar_style(self, active_index):
        """更新导航按钮样式"""
        for idx, (btn, _) in self.steps.items():
            if idx == active_index:
                btn.setStyleSheet("background: #e0f0ff;")
            else:
                btn.setStyleSheet("")


    def on_save_clicked(self):
        """保存按钮点击处理"""
        if self.validate_current_step():
            self.current_step += 1
            self.switch_page(self.current_step)
            self.update_right_panel()
    
    def validate_current_step(self):
        """验证当前步骤数据完整性"""
        if self.current_step == 0:  # 基本信息页验证
            return self.validate_basic_info()
        # 其他步骤的验证逻辑...
        return True
    
    def validate_basic_info(self):
        """验证必填字段"""
        info = self.bid_data.info
        required_fields = {
            "项目名称": info.project_name,
            "投标人": info.bidder,
            "统一信用代码": info.bidder_credit_code
        }
        
        missing = [name for name, value in required_fields.items() if not value.strip()]
        if missing:
            QtWidgets.QMessageBox.warning(self, "数据不完整", f"以下字段必填：{', '.join(missing)}")
            return False
        return True



if __name__ == "__main__":
    import sys
    
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
