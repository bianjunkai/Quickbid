from PyQt5.QtWidgets import QWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QToolBar, QAction
from PyQt5.QtCore import Qt

class OutlinePage(QWidget):
    def __init__(self, data_model):
        super().__init__()
        self.data = data_model
        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # 工具栏
        self.toolbar = QToolBar()
        self.add_action = QAction("添加章节", self)
        self.remove_action = QAction("删除章节", self)
        self.toolbar.addActions([self.add_action, self.remove_action])
        
        # 树形目录编辑器
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("标书目录结构")
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["标题", "自动编号"])
        
        # 初始化根节点
        root = QTreeWidgetItem(self.tree)
        root.setText(0, "标书根目录")
        root.setFlags(root.flags() | Qt.ItemIsEditable)
        
        layout.addWidget(self.toolbar)
        layout.addWidget(self.tree)
        self.setLayout(layout)

    def setup_connections(self):
        self.add_action.triggered.connect(self.add_section)
        self.remove_action.triggered.connect(self.remove_section)
        self.tree.itemChanged.connect(self.update_numbering)

    def add_section(self):
        selected = self.tree.currentItem()
        new_item = QTreeWidgetItem()
        new_item.setText(0, "新章节")
        new_item.setFlags(new_item.flags() | Qt.ItemIsEditable)
        
        # 设置level属性
        if selected:
            new_item.level = selected.level + 1
            selected.addChild(new_item)
        else:
            new_item.level = 0
            self.tree.addTopLevelItem(new_item)
        
        self.update_numbering()

    def remove_section(self):
        item = self.tree.currentItem()
        if item and item.parent():
            item.parent().removeChild(item)
            self.update_numbering()

    def update_numbering(self):
        """递归更新所有节点的自动编号"""
        def _update_item(item, parent_numbers):
            # 处理根节点
            if item.parent() is None:
                current_number = []
            else:
                level = item.parent().level + 1
                if level >= 3:
                    item.setHidden(True)  # 隐藏超过三级的节点
                    return
                
                current_number = parent_numbers.copy()
                current_number.append(str(item.parent().indexOfChild(item) + 1))
            
            # 生成编号字符串（如1.2.3）
            number_str = ".".join(current_number)
            item.setText(1, number_str)
            
            # 递归处理子节点
            for i in range(item.childCount()):
                _update_item(item.child(i), current_number)

        # 从根节点开始更新
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            _update_item(root.child(i), [])
