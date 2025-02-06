from dataclasses import dataclass
from PyQt5.QtCore import QObject, pyqtSignal

@dataclass
class ProjectInfo:
    # 基础信息
    project_name: str = ""
    project_code: str = ""
    
    # 招标方信息
    tender_org: str = ""
    tender_agent: str = ""
    
    # 投标方信息
    bidder: str = ""
    bidder_legal_rep: str = ""
    bidder_credit_code: str = ""
    bidder_address: str = ""
    bidder_legal_phone: str = ""
    bidder_legal_id: str = ""
    
    # 授权代表信息
    authorized_rep: str = ""
    authorized_phone: str = ""
    authorized_id: str = ""

class BidData(QObject):
    info_updated = pyqtSignal()  # 数据更新信号
    property_changed = pyqtSignal(str, object)  # 属性变更信号
    
    def __init__(self):
        super().__init__()
        self.info = ProjectInfo()
        self._setup_bindings()
        
    def _setup_bindings(self):
        """设置数据绑定"""
        for field in self.info.__dataclass_fields__:
            setattr(self.info.__class__, field, self._create_property(field))
            
    def _create_property(self, field):
        """创建属性描述符"""
        def getter(obj):
            return getattr(obj, f"_{field}")
            
        def setter(obj, value):
            setattr(obj, f"_{field}", value)
            self.property_changed.emit(field, value)
            self.info_updated.emit()
            
