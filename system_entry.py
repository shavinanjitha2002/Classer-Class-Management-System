import mysql.connector as mysql
import json5, os
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QGridLayout, QStackedWidget, QHBoxLayout,
                             QCheckBox, QStackedLayout, QLineEdit, QScrollArea, QCompleter, QMessageBox)
from PyQt5.QtCore import Qt,QSize, QDate, QTime, QTimer, pyqtSignal
from PyQt5.QtGui import QKeyEvent, QPixmap, QIcon

from util.logger import Logger
from util.security.access import AccessManager

from widget.link_button import LinkButton, CommandLinkButton
from panel.section_panel import SectionPanel
from panel.search_result_panel import SearchResultPanel

from SECTION_INDEXES import SUB_SECTION_INDEXES, KEYWORDS_MAP
from util.common_functions import getAccessIndexes, checkAccessPreviliage
####################### end of import files ##########################
global connection, logger, accessManager
connection : mysql.MySQLConnection = None
logger : Logger = None
accessManager : AccessManager = None

LINK_BUTTON_DETAILS = [
    ("Student Manager", "add new students, update, edit and search/view students", "resources/icons/widget.png"),
    ("Class Manager", "manage classes, create new class, modify and setup class", "resources/icons/home-white.png"),
    ("Registers", "start new registers, view registers and search registers", "resources/icons/admin-profile.png"),
    ("Payments", "manage payments, view payment history and manage it", "resources/icons/user.png"),
    ("Task Manager", "manage classes, create new class, modify and setup class", "resources/icons/widget.png"),
    ("Task Manager", "manage classes, create new class, modify and setup class", "resources/icons/widget.png")
]

class SystemPanel(QWidget):

    quitSignal = pyqtSignal()
    logoutSignal = pyqtSignal()

    def __init__(self, _connection : mysql.MySQLConnection, _logger : Logger, _access_manager : AccessManager, *args, **kwargs):
        super(SystemPanel, self).__init__()
        global connection, logger, accessManager
        connection = _connection
        logger = _logger
        accessManager = _access_manager
        # initiate the UI
        self.initializeUI()


    # static part of UI
    def initializeUI(self):

        # create stack layout
        self.stackLayout = QStackedLayout()
        self.stackLayout.setContentsMargins(0, 0, 0, 0)
        # create Index Panel
        self.createIndexPanel()

        # create search result panel
        self.createSearchResultPanel()

        self.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.stackLayout)

    def createSearchResultPanel(self):

        # create search panel
        self.searchResultPanel = SearchResultPanel()
        self.searchResultPanel.homeSignal.connect(lambda : self.stackLayout.setCurrentWidget(self.indexPanel))
        self.searchResultPanel.searchSignal.connect(lambda e : self.addPanel(*e))

        # add to stack layout of main window
        self.stackLayout.addWidget(self.searchResultPanel)

    def createIndexPanel(self):

        self.panelStack = {}

        # index panel widget
        self.indexPanel = QWidget()
        self.indexPanel.setObjectName("main")
        self.indexPanel.setContentsMargins(0, 0, 0, 0)

        # create top bar of the index panel
        top_grid = self.createTopIndexPanel()
        # create links layout
        linkScrollArea = self.createLinkLayout()
        # create bottom bar of index panel
        bottom_grid = self.createBottomGrid()

        # setup index panel
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addLayout(top_grid)
        vbox.addWidget(linkScrollArea)
        vbox.addLayout(bottom_grid)
        self.indexPanel.setLayout(vbox)

        self.stackLayout.addWidget(self.indexPanel)

    def createTopIndexPanel(self) -> QGridLayout:

        self.timeLabel = QLabel(QTime.currentTime().toString("hh:mm"))
        self.dateLabel = QLabel(QDate.currentDate().toString("dddd, MMM dd"))

        self.timeLabel.setObjectName("time-label")
        self.dateLabel.setObjectName("date-label")

        # create timer for update date and time
        self.timer = QTimer()
        self.timer.start(1000)
        self.timer.timeout.connect(self.updateDateAndTime)

        completer = QCompleter([str(item[1]) for item in SUB_SECTION_INDEXES.values()])
        completer.setCaseSensitivity(Qt.CaseInsensitive)

        # create search bar
        self.searchBar = QLineEdit()
        self.searchBar.setMaximumWidth(500)
        self.searchBar.setPlaceholderText("Find Sections and Sub Sections")
        self.searchBar.setObjectName("search-bar")
        self.searchBar.returnPressed.connect(lambda e = self.searchBar : self.searchSections(e))
        self.searchBar.setCompleter(completer)

        searchIcon = QLabel()
        searchIcon.setPixmap(QPixmap("resources/icons/search.png").scaled(QSize(30, 30), Qt.KeepAspectRatio,
                                                                          Qt.FastTransformation))
        hbox = QHBoxLayout()
        hbox.addSpacing(150)
        hbox.addWidget(searchIcon)
        hbox.addSpacing(10)
        hbox.addWidget(self.searchBar)
        hbox.addStretch()

        close_button = QPushButton("X")
        close_button.pressed.connect(lambda: self.quitSignal.emit())

        # create grid layout
        top_grid = QGridLayout()
        top_grid.setContentsMargins(0, 0, 0, 0)
        top_grid.addWidget(self.timeLabel, 0, 0, alignment=Qt.AlignLeft)
        top_grid.addWidget(self.dateLabel, 1, 0, alignment=Qt.AlignLeft)
        top_grid.addLayout(hbox, 0, 1, 2, 1, alignment=Qt.AlignCenter)
        top_grid.addWidget(close_button, 0, 2, alignment=Qt.AlignTop | Qt.AlignRight)

        return top_grid

    def createLinkLayout(self) -> QScrollArea:

        # create command link section of index panel
        linkScrollArea = QScrollArea()
        linkScrollArea.setObjectName("link-scroll-pane")
        linkScrollArea.setWidgetResizable(True)
        linkScrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        linkScrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        linkWidget = QWidget()
        linkScrollArea.setWidget(linkWidget)

        self.linkLayout = QGridLayout()
        self.linkLayout.setSpacing(20)
        linkWidget.setLayout(self.linkLayout)

        # load the access indexes for main sections
        accessIndex = getAccessIndexes(0)

        for i in range(len(LINK_BUTTON_DETAILS)):
            linkButton = LinkButton(*LINK_BUTTON_DETAILS[i], i)
            linkButton.clicked_signal.connect(self.addPanel)
            if not checkAccessPreviliage(accessIndex, i, accessManager.session["level"]):
                linkButton.setDisabled(True)

            self.linkLayout.addWidget(linkButton, i//5 ,i%5)


        return linkScrollArea

    def createBottomGrid(self) -> QGridLayout:

        grid = QGridLayout()

        # create main section link button for system backend working and additional things
        logggerButton = CommandLinkButton("Logger", "view log files, search and more", "resources/icons/logger.png")
        adminProfileButton = CommandLinkButton("Admin Profile", "view admin profile, update, edit, add fields",
                                               "resources/icons/admin-profile.png")
        userAccountButton = CommandLinkButton("Users", "view user account, update, remove, change",
                                               "resources/icons/user.png")

        # get access privilege indexes
        accessIndexes = getAccessIndexes(0)
        buttonMap = {
            -1 : logggerButton,
            -2 : adminProfileButton,
            -3 : userAccountButton
        }
        for i, button in buttonMap.items():
            if not checkAccessPreviliage(accessIndexes, i, accessManager.session["level"]):
                button.setDisabled(True)


        # create logout button for system logout behaviour
        logoutButton = QPushButton()
        logoutButton.setIcon(QIcon("resources/icons/logout.png"))
        logoutButton.setIconSize(QSize(60, 60))
        logoutButton.setObjectName("logout-button")
        logoutButton.pressed.connect(self.close)

        grid.addWidget(logggerButton, 0, 0)
        grid.addWidget(adminProfileButton, 0, 1)
        grid.addWidget(userAccountButton, 0, 2)
        grid.addWidget(logoutButton, 0, 5, alignment=Qt.AlignRight|Qt.AlignBottom)

        return grid


    # dynamical behavior of UI
    def updateDateAndTime(self):

        self.dateLabel.setText(QDate.currentDate().toString("dddd MMM, dd"))
        self.timeLabel.setText(QTime.currentTime().toString("hh:mm"))

    def addPanel(self, section_id : int, sub_section_id : int = 0):

        if section_id in self.panelStack.keys():
            self.stackLayout.setCurrentIndex(self.panelStack.get(section_id, 0))
            # set subsection - updated
            self.stackLayout.currentWidget().displayPanel(sub_section_id)
            self.stackLayout.currentWidget().setCurrentLinkButtonByIndex(sub_section_id)
        else:
            # create instance of panel that matches to section id that pass to method
            panel = self.createPanel(section_id, sub_section_id)
            # add to stack layout
            self.stackLayout.addWidget(panel)
            self.stackLayout.setCurrentWidget(panel)

            # add to panel stack
            self.panelStack[section_id] = self.stackLayout.currentIndex()

    def createPanel(self, section_id : int, sub_section_id : int) -> QWidget:

        if section_id == 0:
            panel = SectionPanel(section_id, ["Add Student", "Student Table", "Student Search"], "Student Manager", sub_section_id,
                                 parent=self, access_manager_= accessManager)
        elif section_id == 1:
            return QLabel("Class", parent=self)
        else:
            return QLabel("Register", parent=self)

        panel.back_signal.connect(lambda : self.stackLayout.setCurrentWidget(self.indexPanel))
        return panel


    # search functionalities
    def isDirectKeyWord(self, keyword : str) -> bool:

        # first check keyword in the subsection keywords
        for section, text, sub_section in SUB_SECTION_INDEXES.values():
            if text.lower() == keyword.lower():
                return True
        return False

    def getDirectIndexes(self, keyword : str) -> tuple[int]:

        for section, text, sub_section in SUB_SECTION_INDEXES.values():
            if text.lower() == keyword.lower():
                return (section, sub_section)

    def getSearchResult(self, keyword : str) -> list[tuple[int]]:

        sub_section_ids = []
        for keys, sub_section_id in KEYWORDS_MAP.items():
            if keyword.lower().strip() in keys.lower():
                sub_section_ids.append(sub_section_id)
        # remove all duplicates things
        sub_section_ids = set(sub_section_ids)

        results = []
        for i in sub_section_ids:
            results.append(SUB_SECTION_INDEXES[i])

        return results

    def searchSections(self, searchBar : QLineEdit):

        keyword = searchBar.text()
        if self.isDirectKeyWord(keyword):
            section_id, sub_section_id = self.getDirectIndexes(keyword)
            self.addPanel(section_id, sub_section_id)

        else:
            index_results = self.getSearchResult(keyword)

            # self.fillSearchResult(index_results)
            self.searchResultPanel.addSearchResults(index_results)
            self.stackLayout.setCurrentWidget(self.searchResultPanel)


    # overwrite methods - standard methods
    def keyPressEvent(self, event : QKeyEvent) -> None:

        if event.key() == Qt.Key_Backspace:
            self.stackLayout.setCurrentWidget(self.indexPanel)

    def close(self) -> bool:

        msg = QMessageBox.question(self, "Logout System", "Are you sure to logout from system?")
        if msg == QMessageBox.StandardButton.Yes:
            # end the session
            accessManager.endSession()
            self.logoutSignal.emit()

