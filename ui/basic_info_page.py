from PyQt5.QtWidgets import QWidget, QFormLayout, QLineEdit, QScrollArea
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtCore import QRegExp

class BasicInfoPage(QScrollArea):
    def __init__(self, data_model):
        super().__init__()
        self.data = data_model
        self.init_ui()
        self.setup_validators()
        
    def init_ui(self):
        # 主容器
        container = QWidget()
        layout = QFormLayout()
        
        # 项目信息
        self.project_name = self._create_line_edit("项目名称", self.data.info.project_name)
        self.project_code = self._create_line_edit("项目编号", self.data.info.project_code)
        
        # 招标方信息
        self.tender_org = self._create_line_edit("招标人", self.data.info.tender_org)
        self.tender_agent = self._create_line_edit("招标代理", self.data.info.tender_agent)
        
        # 投标方信息
        self.bidder = self._create_line_edit("投标人", self.data.info.bidder)
        self.bidder_legal_rep = self._create_line_edit("法人代表", self.data.info.bidder_legal_rep)
        self.bidder_credit_code = self._create_line_edit("统一信用代码", self.data.info.bidder_credit_code)
        self.bidder_address = self._create_line_edit("联系地址", self.data.info.bidder_address)
        
        # 联系信息
        self.bidder_legal_phone = self._create_line_edit("法人手机", self.data.info.bidder_legal_phone)
        self.bidder_legal_id = self._create_line_edit("法人身份证", self.data.info.bidder_legal_id)
        
        # 授权代表
        self.authorized_rep = self._create_line_edit("授权代表", self.data.info.authorized_rep)
        self.authorized_phone = self._create_line_edit("授权代表手机", self.data.info.authorized_phone)
        self.authorized_id = self._create_line_edit("授权代表身份证", self.data.info.authorized_id)
        
        # 添加到布局
        layout.addRow("=== 项目信息 ===", QWidget())
        layout.addRow("项目名称：", self.project_name)
        layout.addRow("项目编号：", self.project_code)
        
        layout.addRow("=== 招标方信息 ===", QWidget())
        layout.addRow("招标人：", self.tender_org)
        layout.addRow("招标代理：", self.tender_agent)
        
        layout.addRow("=== 投标方信息 ===", QWidget())
        layout.addRow("投标人：", self.bidder)
        layout.addRow("法人代表：", self.bidder_legal_rep)
        layout.addRow("统一信用代码：", self.bidder_credit_code)
        layout.addRow("联系地址：", self.bidder_address)
        
        layout.addRow("=== 联系方式 ===", QWidget())
        layout.addRow("法人手机：", self.bidder_legal_phone)
        layout.addRow("法人身份证：", self.bidder_legal_id)
        
        layout.addRow("=== 授权代表 ===", QWidget())
        layout.addRow("授权代表：", self.authorized_rep)
        layout.addRow("授权手机：", self.authorized_phone)
        layout.addRow("授权身份证：", self.authorized_id)
        
        container.setLayout(layout)
        self.setWidget(container)
        self.setWidgetResizable(True)
    
    def _create_line_edit(self, field_name, default_value=""):
        """创建带数据绑定的输入框"""
        edit = QLineEdit(default_value)
        edit.setPlaceholderText(f"请输入{field_name}")
        edit.textChanged.connect(lambda text: self._update_data(field_name, text))
        return edit
    
    def _update_data(self, field, value):
        """更新数据模型"""
        setattr(self.data.info, field, value)
        self.data.info_updated.emit()
    
    def setup_validators(self):
        """设置输入验证规则"""
        # 手机号验证（11位数字）
        phone_re = QRegExp("^\\d{11}$")
        self.bidder_legal_phone.setValidator(QRegExpValidator(phone_re, self))
        self.authorized_phone.setValidator(QRegExpValidator(phone_re, self))
        
        # 身份证验证（15/18位）
        id_re = QRegExp("^\\d{15}|\\d{17}[0-9X]$")
        self.bidder_legal_id.setValidator(QRegExpValidator(id_re, self))
        self.authorized_id.setValidator(QRegExpValidator(id_re, self))
        
        # 信用代码验证（18位字母数字）
        credit_re = QRegExp("^[A-Z0-9]{18}$")
        self.bidder_credit_code.setValidator(QRegExpValidator(credit_re, self))