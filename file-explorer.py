import sys
import os
import shutil
import datetime
from PyQt6.QtGui import (QFileSystemModel, QDesktopServices, QAction, QIcon, 
                         QKeySequence, QDrag)
from PyQt6.QtCore import (QDir, Qt, QSize, QUrl, QMimeData, QFileInfo)
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTreeView, QSplitter, QLineEdit, 
                             QPushButton, QAbstractItemView, QMenu, QMessageBox, 
                             QInputDialog, QLabel, QDialog, QFormLayout)

class FilePropertiesDialog(QDialog):
    """プロパティを表示するダイアログ"""
    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("プロパティ")
        self.setMinimumWidth(300)
        
        info = QFileInfo(path)
        layout = QFormLayout(self)
        
        # ファイル名
        layout.addRow("名前:", QLabel(info.fileName()))
        # パス
        layout.addRow("場所:", QLabel(info.absolutePath()))
        # サイズ
        size_str = f"{info.size() / 1024:.2f} KB" if info.isFile() else "フォルダー"
        layout.addRow("サイズ:", QLabel(size_str))
        # 日付
        created = info.birthTime().toString("yyyy/MM/dd HH:mm:ss")
        modified = info.lastModified().toString("yyyy/MM/dd HH:mm:ss")
        layout.addRow("作成日時:", QLabel(created))
        layout.addRow("更新日時:", QLabel(modified))
        # 属性
        attribs = []
        if info.isReadable(): attribs.append("読取")
        if info.isWritable(): attribs.append("書込")
        if info.isHidden(): attribs.append("隠し")
        layout.addRow("属性:", QLabel(", ".join(attribs)))

class AdvancedFileManager(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Python Advanced Explorer")
        self.setGeometry(100, 100, 1100, 700)
        
        # 内部変数: 切り取り操作かどうかを判定するフラグ
        self.is_cut_operation = False 
        self.cut_paths = [] 

        # --- モデル設定 ---
        self.model = QFileSystemModel()
        self.model.setRootPath("")
        self.model.setReadOnly(False) # リネームなどを許可
        self.model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot | QDir.Filter.AllDirs)

        # --- UI構築 ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # アドレスバーエリア
        top_bar = QHBoxLayout()
        self.btn_up = QPushButton("↑ 親フォルダ")
        self.btn_up.clicked.connect(self.navigate_up)
        
        self.path_edit = QLineEdit()
        self.path_edit.returnPressed.connect(self.navigate_to_path)
        
        self.btn_refresh = QPushButton("更新")
        self.btn_refresh.clicked.connect(self.refresh_view)

        top_bar.addWidget(self.btn_up)
        top_bar.addWidget(self.path_edit)
        top_bar.addWidget(self.btn_refresh)
        main_layout.addLayout(top_bar)

        # スプリッター
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- 左ペイン (ツリー) ---
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(""))
        for i in range(1, 4): self.tree.setColumnHidden(i, True)
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(20)
        self.tree.setSortingEnabled(True)
        self.tree.clicked.connect(self.on_tree_clicked)
        
        # --- 右ペイン (リスト) ---
        self.table = QTreeView()
        self.table.setModel(self.model)
        self.table.setRootIsDecorated(False)
        self.table.setSortingEnabled(True)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setDragEnabled(True)
        self.table.setAcceptDrops(True)
        self.table.setDropIndicatorShown(True)
        self.table.doubleClicked.connect(self.on_table_double_clicked)
        
        # 右クリックメニューの有効化
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_context_menu)

        splitter.addWidget(self.tree)
        splitter.addWidget(self.table)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        main_layout.addWidget(splitter)

        # 初期パス
        self.navigate_to_directory(QDir.homePath())
        
        # ショートカットキーの設定
        self.setup_shortcuts()

    def setup_shortcuts(self):
        # コピー (Ctrl+C)
        QAction("Copy", self, shortcut=QKeySequence.StandardKey.Copy, triggered=self.action_copy).add_to(self.table)
        # 貼り付け (Ctrl+V)
        QAction("Paste", self, shortcut=QKeySequence.StandardKey.Paste, triggered=self.action_paste).add_to(self.table)
        # 切り取り (Ctrl+X)
        QAction("Cut", self, shortcut=QKeySequence.StandardKey.Cut, triggered=self.action_cut).add_to(self.table)
        # 削除 (Delete)
        QAction("Delete", self, shortcut=QKeySequence.StandardKey.Delete, triggered=self.action_delete).add_to(self.table)
        # リネーム (F2)
        QAction("Rename", self, shortcut="F2", triggered=self.action_rename).add_to(self.table)
        # 全選択 (Ctrl+A)
        QAction("Select All", self, shortcut=QKeySequence.StandardKey.SelectAll, triggered=self.table.selectAll).add_to(self.table)

    def navigate_to_directory(self, path):
        idx = self.model.index(path)
        if idx.isValid():
            self.table.setRootIndex(idx)
            self.path_edit.setText(path)
            self.tree.setCurrentIndex(idx)
            self.tree.expand(idx)

    def on_tree_clicked(self, index):
        self.navigate_to_directory(self.model.filePath(index))

    def on_table_double_clicked(self, index):
        path = self.model.filePath(index)
        if self.model.isDir(index):
            self.navigate_to_directory(path)
        else:
            try:
                os.startfile(path)
            except:
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def navigate_up(self):
        parent_dir = QDir(self.path_edit.text())
        if parent_dir.cdUp():
            self.navigate_to_directory(parent_dir.absolutePath())

    def navigate_to_path(self):
        path = self.path_edit.text()
        if os.path.exists(path) and os.path.isdir(path):
            self.navigate_to_directory(path)
    
    def refresh_view(self):
        # 現在のパスでリロードを試みる
        current = self.path_edit.text()
        self.navigate_to_directory(current)

    # --- コンテキストメニュー ---
    def open_context_menu(self, position):
        menu = QMenu()
        
        # 選択があるか確認
        indexes = self.table.selectedIndexes()
        has_selection = len(indexes) > 0
        
        # アクション定義
        action_open = menu.addAction("開く")
        menu.addSeparator()
        action_copy = menu.addAction("コピー (Ctrl+C)")
        action_cut = menu.addAction("切り取り (Ctrl+X)")
        action_paste = menu.addAction("貼り付け (Ctrl+V)")
        menu.addSeparator()
        action_rename = menu.addAction("名前の変更 (F2)")
        action_delete = menu.addAction("削除 (Delete)")
        menu.addSeparator()
        action_new_folder = menu.addAction("新規フォルダー")
        menu.addSeparator()
        action_props = menu.addAction("プロパティ")

        # 状態に応じて有効/無効化
        if not has_selection:
            action_open.setEnabled(False)
            action_copy.setEnabled(False)
            action_cut.setEnabled(False)
            action_rename.setEnabled(False)
            action_delete.setEnabled(False)
            action_props.setEnabled(False)
        
        # クリップボードにデータがあるか確認
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        if not mime_data.hasUrls():
            action_paste.setEnabled(False)

        # 実行
        action = menu.exec(self.table.viewport().mapToGlobal(position))

        if action == action_open:
            self.on_table_double_clicked(indexes[0])
        elif action == action_copy:
            self.action_copy()
        elif action == action_cut:
            self.action_cut()
        elif action == action_paste:
            self.action_paste()
        elif action == action_delete:
            self.action_delete()
        elif action == action_rename:
            self.action_rename()
        elif action == action_props:
            self.action_properties()
        elif action == action_new_folder:
            self.action_new_folder()

    # --- アクションの実装 ---
    
    def get_selected_paths(self):
        """選択されているアイテム（行）のフルパスリストを取得"""
        indexes = self.table.selectionModel().selectedRows()
        return [self.model.filePath(idx) for idx in indexes]

    def action_copy(self):
        paths = self.get_selected_paths()
        if not paths: return

        self.is_cut_operation = False
        mime_data = QMimeData()
        urls = [QUrl.fromLocalFile(p) for p in paths]
        mime_data.setUrls(urls)
        QApplication.clipboard().setMimeData(mime_data)

    def action_cut(self):
        paths = self.get_selected_paths()
        if not paths: return
        
        # 切り取りの場合、貼り付け時に「移動」操作を行うためのフラグを立てる
        # OS標準クリップボードへの反映
        self.is_cut_operation = True
        self.cut_paths = paths # 内部で保持（OSクリップボードには属性がないため）
        
        mime_data = QMimeData()
        urls = [QUrl.fromLocalFile(p) for p in paths]
        mime_data.setUrls(urls)
        QApplication.clipboard().setMimeData(mime_data)

    def action_paste(self):
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        
        if not mime_data.hasUrls():
            return

        dest_dir = self.model.filePath(self.table.rootIndex())
        urls = mime_data.urls()

        try:
            for url in urls:
                src_path = url.toLocalFile()
                file_name = os.path.basename(src_path)
                dest_path = os.path.join(dest_dir, file_name)

                # 重複回避ロジック
                if os.path.exists(dest_path):
                    base, ext = os.path.splitext(file_name)
                    counter = 1
                    while os.path.exists(dest_path):
                        dest_path = os.path.join(dest_dir, f"{base}_copy{counter}{ext}")
                        counter += 1

                # 切り取り（移動）かコピーか
                # 内部フラグとパスが一致する場合のみ移動とみなす
                is_move = self.is_cut_operation and (src_path in self.cut_paths)

                if is_move:
                    shutil.move(src_path, dest_path)
                else:
                    if os.path.isdir(src_path):
                        shutil.copytree(src_path, dest_path)
                    else:
                        shutil.copy2(src_path, dest_path)
            
            # 移動完了後はフラグをリセット
            if self.is_cut_operation:
                self.is_cut_operation = False
                self.cut_paths = []
                # クリップボードをクリア
                QApplication.clipboard().clear()

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"操作に失敗しました:\n{str(e)}")

    def action_delete(self):
        paths = self.get_selected_paths()
        if not paths: return

        # 確認ダイアログ
        msg = f"{len(paths)} 個の項目を完全に削除しますか？\n（ゴミ箱には移動せず、直接削除されます）"
        reply = QMessageBox.question(self, "削除の確認", msg, 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                for path in paths:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"削除できませんでした:\n{str(e)}")

    def action_rename(self):
        indexes = self.table.selectionModel().selectedRows()
        if len(indexes) != 1: return

        index = indexes[0]
        old_path = self.model.filePath(index)
        old_name = self.model.fileName(index)
        
        new_name, ok = QInputDialog.getText(self, "名前の変更", "新しい名前:", text=old_name)
        
        if ok and new_name and new_name != old_name:
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            try:
                os.rename(old_path, new_path)
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"名前を変更できませんでした:\n{str(e)}")

    def action_properties(self):
        paths = self.get_selected_paths()
        if not paths: return
        
        # 複数選択時は最初のファイルのみ表示（簡易実装）
        target_path = paths[0]
        dialog = FilePropertiesDialog(target_path, self)
        dialog.exec()

    def action_new_folder(self):
        current_dir = self.model.filePath(self.table.rootIndex())
        new_folder_name, ok = QInputDialog.getText(self, "新規フォルダー", "フォルダー名:")
        
        if ok and new_folder_name:
            target = os.path.join(current_dir, new_folder_name)
            try:
                os.makedirs(target)
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"作成できませんでした:\n{str(e)}")

# helper function to add action to widget
def add_to_widget(self, widget):
    widget.addAction(self)
QAction.add_to = add_to_widget

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AdvancedFileManager()
    window.show()
    sys.exit(app.exec())
    