import sys
import random
import multiprocessing as mp
from PyQt5.QtWidgets import (QApplication, QDialog, QLabel, QLineEdit, 
                            QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox)
from PyQt5.QtGui import QPixmap, QColor, QPainter, QFont
from PyQt5.QtCore import Qt
from GUI import UnmixingGUI
import os
from PyQt5.QtGui import QIcon

# 获取图标绝对路径
def get_icon_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base_dir, "app_icon.ico")
    
    # 验证图标文件存在性
    if not os.path.exists(icon_path):
        raise FileNotFoundError(f"图标文件缺失: {icon_path}")
        
    return icon_path

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.generate_captcha()
        # 设置窗口图标
        try:
            icon = QIcon(get_icon_path())
            self.setWindowIcon(icon)
        except Exception as e:
            print(f"图标加载失败: {str(e)}")        

    def initUI(self):
        self.setWindowTitle('软件登录')
        # 获取屏幕分辨率
        screen = QApplication.primaryScreen().geometry()
        width = int(screen.width() * 0.12)  # 占屏幕宽度的30%
        height = int(width * 1)        # 保持4:3比例

        self.setFixedSize(width, height)
        
        # 控件定义
        self.lbl_user = QLabel('用户名:', self)
        self.txt_user = QLineEdit(self)
        self.txt_user.setPlaceholderText("请输入用户名")
        
        self.lbl_pwd = QLabel('密码:', self)
        self.txt_pwd = QLineEdit(self)
        self.txt_pwd.setEchoMode(QLineEdit.Password)
        self.txt_pwd.setPlaceholderText("请输入密码")
        
        self.lbl_captcha = QLabel('验证码:', self)
        self.txt_captcha = QLineEdit(self)
        self.txt_captcha.setPlaceholderText("输入右侧验证码")
        self.lbl_captcha_img = QLabel(self)
        self.lbl_captcha_img.setFixedSize(100, 40)
        self.lbl_captcha_img.setStyleSheet("border: 1px solid #aaa;")
        self.lbl_captcha_img.mousePressEvent = self.refresh_captcha
        
        # 按钮
        btn_login = QPushButton('登录', self)
        btn_login.clicked.connect(self.verify_login)
        btn_cancel = QPushButton('取消', self)
        btn_cancel.clicked.connect(self.reject)

        # 布局设置
        captcha_layout = QHBoxLayout()
        captcha_layout.addWidget(self.txt_captcha)
        captcha_layout.addWidget(self.lbl_captcha_img)

        form_layout = QVBoxLayout()
        form_layout.addWidget(self.lbl_user)
        form_layout.addWidget(self.txt_user)
        form_layout.addWidget(self.lbl_pwd)
        form_layout.addWidget(self.txt_pwd)
        form_layout.addWidget(self.lbl_captcha)
        form_layout.addLayout(captcha_layout)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(btn_login)
        button_layout.addWidget(btn_cancel)

        main_layout = QVBoxLayout()
        main_layout.addLayout(form_layout)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

        # 样式美化
        self.setStyleSheet("""
            QDialog { background: #f0f0f0; }
            /* 修改所有QLabel字体大小 */
            QLabel { 
                font: 20px '微软雅黑';  /* 修改16px为需要的大小 */
                color: #666; 
            }
            /* 修改所有输入框字体大小 */
            QLineEdit { 
                font: 16px '微软雅黑';  /* 修改16px */
                padding: 8px; 
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            /* 修改按钮字体大小 */
            QPushButton {
                font: 16px '微软雅黑';  /* 修改16px */
                background: #0078d4;
                color: white;
                padding: 8px 20px;
                border-radius: 4px;
            }
        """)

    def generate_captcha(self):
        """生成4位随机验证码（数字+字母）"""
        chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
        self.captcha = ''.join(random.choices(chars, k=4))
        
        # 生成验证码图片
        pixmap = QPixmap(100, 40)
        pixmap.fill(QColor(255,255,255))
        
        painter = QPainter(pixmap)
        painter.setFont(QFont('Arial', 18))
        for i, c in enumerate(self.captcha):
            painter.setPen(QColor(random.randint(0,120), 
                                random.randint(0,120),
                                random.randint(0,120)))
            painter.drawText(20*i+5, 30, c)
        
        # 添加干扰线
        for _ in range(5):
            painter.setPen(QColor(random.randint(50,200),
                                random.randint(50,200),
                                random.randint(50,200)))
            painter.drawLine(
                random.randint(0,100), random.randint(0,40),
                random.randint(0,100), random.randint(0,40)
            )
        painter.end()
        
        self.lbl_captcha_img.setPixmap(pixmap)

    def refresh_captcha(self, event):
        """点击验证码图片刷新"""
        self.generate_captcha()

    def verify_login(self):
        """验证登录信息"""
        username = self.txt_user.text().strip()
        password = self.txt_pwd.text()
        captcha = self.txt_captcha.text().upper()
        
        # 基础验证逻辑（可替换为数据库验证）
        if not all([username, password, captcha]):
            QMessageBox.warning(self, '错误', '所有字段必须填写！')
            return
            
        if captcha != self.captcha:
            QMessageBox.warning(self, '错误', '验证码不正确！')
            self.generate_captcha()
            return
            
        # 示例验证（实际应连接数据库）
        if username == 'admin' and password == 'admin':
            self.accept()
        else:
            QMessageBox.critical(self, '拒绝访问', '用户名或密码错误')
            self.txt_pwd.clear()
            self.txt_captcha.clear()
            self.generate_captcha()

if __name__ == '__main__':
    mp.freeze_support()

    app = QApplication(sys.argv)
    
    # 先显示登录窗口
    login = LoginDialog()
    if login.exec_() == QDialog.Accepted:
        window = UnmixingGUI()
        window.show()
        sys.exit(app.exec_())
    else:
        sys.exit(0)