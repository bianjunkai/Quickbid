from PyQt5.QtWidgets import QWidget, QFormLayout, QLineEdit, QDateEdit
from PyQt5.QtCore import QDate

class InfoPage(QWidget):
    def __init__(self, data_model):
        super().__init__()
        self.data = data_model
        self.init_ui()
        
    def init_ui(self):
        layout = QFormLayout()
        
        # 项目名称
        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(
            lambda: setattr(self.data.info, 'name', self.name_edit.text()))
        layout.addRow("项目名称：", self.name_edit)
        
        # 公司名称
        self.company_edit = QLineEdit()
        self.company_edit.textChanged.connect(
            lambda: setattr(self.data.info, 'company', self.company_edit.text()))
        layout.addRow("公司名称：", self.company_edit)
        
        # 标书编号（自动生成示例）
        self.bid_num_edit = QLineEdit()
        self.bid_num_edit.setPlaceholderText("例如：BID-2024-001")
        self.bid_num_edit.textChanged.connect(
            lambda: setattr(self.data.info, 'bid_number', self.bid_num_edit.text()))
        layout.addRow("标书编号：", self.bid_num_edit)
        
        # 截止日期
        self.deadline_edit = QDateEdit()
        self.deadline_edit.setDate(QDate.currentDate().addDays(7))
        self.deadline_edit.dateChanged.connect(
            lambda d: setattr(self.data.info, 'deadline', d.toPyDate()))
        layout.addRow("截止日期：", self.deadline_edit)
        
        self.setLayout(layout)