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
    
    def __init__(self):
        super().__init__()
        self.info = ProjectInfo()