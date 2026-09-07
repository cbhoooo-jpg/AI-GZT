; *** Inno Setup version 6.0.0+ Chinese Simplified messages ***
; 翻译作者:jflinch <jflinch@163.com>
; 最后更新:2023-01-01

[LangOptions]
; The following three entries are very important. Be sure to read and
; understand the '[LangOptions] section' topic in the help file.
LanguageName=简体中文
LanguageID=$0804
LanguageCodePage=936
; If the language you are translating to requires special font faces or
; sizes, uncomment any of the following entries and change them accordingly.
;DialogFontName=
;DialogFontSize=8
;WelcomeFontName=Verdana
;WelcomeFontSize=12
;TitleFontName=Arial
;TitleFontSize=29
;CopyrightFontName=Arial
;CopyrightFontSize=8

[Messages]
SetupAppTitle=安装
SetupWindowTitle=安装 - %1
UninstallAppTitle=卸载
UninstallAppFullTitle=%1 卸载
InformationTitle=信息
ConfirmTitle=确认
ErrorTitle=错误
SetupLdrStartupMessage=现在将安装 %1。是否继续？
LdrCannotCreateTemp=无法创建临时文件。安装中止
LdrCannotExecTemp=无法在临时目录中解压文件。安装中止
HelpTextNote=
LastErrorMessage=%1。%n%n错误 %2:%3
SetupFileMissing=安装目录中缺少文件 %1。请更正问题或获取程序的新副本。
SetupFileCorrupt=安装文件已损坏，请获取程序的新副本。
SetupFileCorruptOrWrongVer=安装文件已损坏，或与此版本的安装程序不兼容。请更正问题或获取程序的新副本。
InvalidParameter=命令行上传入了无效参数:%n%n%1
SetupAlreadyRunning=安装程序已在运行。
WindowsVersionNotSupported=此程序不支持您计算机正在运行的 Windows 版本。
WindowsServicePackRequired=此程序需要 %1 Service Pack %2 或更高版本。
NotOnThisPlatform=此程序不会在 %1 上运行。
OnlyOnThisPlatform=此程序必须在 %1 上运行。
OnlyOnTheseArchitectures=此程序只能安装在为以下处理器架构设计的 Windows 版本上:%n%n%1
WinVersionTooLowError=此程序需要 %1 %2 或更高版本。
WinVersionTooHighError=此程序无法安装在 %1 %2 或更高版本上。
AdminPrivilegesRequired=安装此程序时您必须以管理员身份登录。
PowerUserPrivilegesRequired=安装此程序时您必须以管理员身份或 Power Users 组成员登录。
SetupAppRunningError=安装程序检测到 %1 正在运行。%n%n请立即关闭它的所有实例，然后点击“确定”继续，或点击“取消”退出。
UninstallAppRunningError=卸载程序检测到 %1 正在运行。%n%n请立即关闭它的所有实例，然后点击“确定”继续，或点击“取消”退出。
PrivilegesRequiredOverrideTitle=选择安装模式
PrivilegesRequiredOverrideInstruction=选择安装模式
PrivilegesRequiredOverrideText1=%1 可以为所有用户安装（需要管理员权限），或仅为您安装。
PrivilegesRequiredOverrideText2=%1 可以仅为您安装，或为所有用户安装（需要管理员权限）。
PrivilegesRequiredOverrideAllUsers=为所有用户安装(&A)
PrivilegesRequiredOverrideAllUsersRecommended=为所有用户安装（推荐）(&A)
PrivilegesRequiredOverrideCurrentUser=仅为我安装(&M)
PrivilegesRequiredOverrideCurrentUserRecommended=仅为我安装（推荐）(&M)
ErrorCreatingDir=无法创建目录“%1”。%n%n%2
ErrorTooManyFilesInDir=无法在目录“%1”中创建文件，因为其中文件过多
ExitSetupTitle=退出安装
ExitSetupMessage=安装尚未完成。如果现在退出，程序将不会被安装。%n%n您可以稍后再次运行安装程序以完成安装。%n%n退出安装吗？
AboutSetupMenuItem=关于安装程序(&A)...
AboutSetupTitle=关于安装
AboutSetupMessage=%1 版本 %2%n%n%3
AboutSetupNote=
TranslatorNote=
ButtonBack=< 上一步(&B)
ButtonNext=下一步(&N) >
ButtonInstall=安装(&I)
ButtonOK=确定
ButtonCancel=取消
ButtonYes=是(&Y)
ButtonYesToAll=全部是(&A)
ButtonNo=否(&N)
ButtonNoToAll=全部否(&O)
ButtonFinish=完成(&F)
ButtonBrowse=浏览(&R)...
ButtonWizardBrowse=浏览(&R)...
ButtonNewFolder=新建文件夹(&M)
SelectLanguageTitle=选择安装语言
SelectLanguageLabel=请选择安装过程中使用的语言。
ClickNext=点击“下一步”继续，或点击“取消”退出安装程序。
BeveledLabel=
BrowseDialogTitle=浏览文件夹
BrowseDialogLabel=请在下面列表中选择文件夹，然后点击“确定”。
NewFolderName=新建文件夹
WelcomeLabel1=欢迎使用 [name] 安装向导
WelcomeLabel2=现在将安装 [name/ver] 到您的计算机中。%n%n建议在继续之前关闭所有其它应用程序。
WizardPassword=密码
PasswordLabel1=此安装受密码保护。
PasswordLabel3=请提供密码，然后点击“下一步”继续。密码区分大小写。
PasswordEditLabel=密码(&P):
IncorrectPassword=您输入的密码不正确，请重试。
WizardLicense=许可协议
LicenseLabel=请在继续之前阅读以下重要信息。
LicenseLabel3=请在继续安装前阅读许可协议，您必须接受协议条款才能继续安装 [name]。
LicenseAccepted=我接受协议(&A)
LicenseNotAccepted=我不接受协议(&D)
WizardInfoBefore=信息
InfoBeforeLabel=请在继续之前阅读以下重要信息。
InfoBeforeClickLabel=准备好继续安装时，请点击“下一步”。
WizardInfoAfter=信息
InfoAfterLabel=请在继续之前阅读以下重要信息。
InfoAfterClickLabel=准备好继续安装时，请点击“下一步”。
WizardUserInfo=用户信息
UserInfoDesc=请输入您的信息。
UserInfoName=用户名(&U):
UserInfoOrg=组织(&O):
UserInfoSerial=序列号(&S):
UserInfoNameRequired=您必须输入用户名。
WizardSelectDir=选择目标位置
SelectDirDesc=您想将 [name] 安装到哪里？
SelectDirLabel3=安装程序将把 [name] 安装到以下文件夹中。
SelectDirBrowseLabel=点击“下一步”继续。如要选择其他文件夹，请点击“浏览”。
DiskSpaceGBLabel=至少需要 [gb] GB 的可用磁盘空间。
DiskSpaceMBLabel=至少需要 [mb] MB 的可用磁盘空间。
CannotInstallToNetworkDrive=安装程序无法安装到网络驱动器。
CannotInstallToUNCPath=安装程序无法安装到 UNC 路径。
InvalidPath=您必须输入带驱动器号的完整路径，例如:%n%nC:\APP%n%n或以下形式的 UNC 路径:%n%n\\server\share
InvalidDrive=您选择的驱动器或 UNC 共享不存在或无法访问，请选择其他位置。
DiskSpaceWarningTitle=磁盘空间不足
DiskSpaceWarning=安装程序至少需要 %1 KB 可用空间，但所选驱动器仅有 %2 KB 可用。%n%n您仍要继续吗？
DirNameTooLong=文件夹名称或路径过长。
InvalidDirName=文件夹名称无效。
BadDirName32=文件夹名称不能包含以下任何字符:%n%n%1
DirExistsTitle=文件夹已存在
DirExists=文件夹:%n%n%1%n%n已存在。您仍要安装到该文件夹吗？
DirDoesntExistTitle=文件夹不存在
DirDoesntExist=文件夹:%n%n%1%n%n不存在。您要创建该文件夹吗？
WizardSelectComponents=选择组件
SelectComponentsDesc=您想安装哪些组件？
SelectComponentsLabel2=选择要安装的组件，清除不想安装的组件。准备好后点击“下一步”。
FullInstallation=完整安装
CompactInstallation=精简安装
CustomInstallation=自定义安装
NoUninstallWarningTitle=组件已存在
NoUninstallWarning=安装程序检测到以下组件已安装在您的计算机上:%n%n%1%n%n取消选择这些组件不会卸载它们。%n%n您仍要继续吗？
ComponentSize1=%1 KB
ComponentSize2=%1 MB
ComponentsDiskSpaceGBLabel=当前选择至少需要 [gb] GB 的可用磁盘空间。
ComponentsDiskSpaceMBLabel=当前选择至少需要 [mb] MB 的可用磁盘空间。
WizardSelectTasks=选择附加任务
SelectTasksDesc=您想执行哪些附加任务？
SelectTasksLabel2=选择安装 [name] 时要执行的附加任务，然后点击“下一步”。
WizardSelectProgramGroup=选择开始菜单文件夹
SelectStartMenuFolderDesc=安装程序应在哪里放置程序的快捷方式？
SelectStartMenuFolderLabel3=安装程序将在以下开始菜单文件夹中创建程序的快捷方式。
SelectStartMenuFolderBrowseLabel=点击“下一步”继续。如要选择其他文件夹，请点击“浏览”。
MustEnterGroupName=您必须输入文件夹名称。
GroupNameTooLong=文件夹名称或路径过长。
InvalidGroupName=文件夹名称无效。
BadGroupName=文件夹名称不能包含以下任何字符:%n%n%1
NoProgramGroupCheck2=不创建开始菜单文件夹(&D)
WizardReady=准备安装
ReadyLabel1=安装程序已准备好在您的计算机上安装 [name]。
ReadyLabel2a=点击“安装”继续安装，或点击“上一步”查看或更改设置。
ReadyLabel2b=点击“安装”继续安装。
ReadyMemoUserInfo=用户信息:
ReadyMemoDir=安装位置:
ReadyMemoType=安装类型:
ReadyMemoComponents=已选组件:
ReadyMemoGroup=开始菜单文件夹:
ReadyMemoTasks=附加任务:
DownloadingLabel2=正在下载文件……
ButtonStopDownload=停止下载(&S)
StopDownload=您确定要停止下载吗？
ErrorDownloadAborted=下载已中止
ErrorDownloadFailed=下载失败:%1 %2
ErrorDownloadSizeFailed=获取大小失败:%1 %2
ErrorProgress=无效的进度:%1 / %2
ErrorFileSize=文件大小无效:应为 %1，实际为 %2
ExtractingLabel=正在解压文件……
ButtonStopExtraction=停止解压(&S)
StopExtraction=您确定要停止解压吗？
ErrorExtractionAborted=解压已中止
ErrorExtractionFailed=解压失败:%1
ArchiveIncorrectPassword=密码不正确
ArchiveIsCorrupted=压缩包已损坏
ArchiveUnsupportedFormat=不支持的压缩包格式
WizardPreparing=准备安装
PreparingDesc=安装程序正准备在您的计算机上安装 [name]。
PreviousInstallNotCompleted=上一个程序的安装/移除未完成，您需要重启计算机以完成该安装。%n%n重启后请再次运行安装程序以完成 [name] 的安装。
CannotContinue=安装程序无法继续，请点击“取消”退出。
ApplicationsFound=以下应用程序正在使用需要由安装程序更新的文件。建议允许安装程序自动关闭这些应用程序。
ApplicationsFound2=以下应用程序正在使用需要由安装程序更新的文件。建议允许安装程序自动关闭这些应用程序。安装完成后，安装程序将尝试重新启动这些应用程序。
CloseApplications=自动关闭应用程序(&A)
DontCloseApplications=不关闭应用程序(&D)
ErrorCloseApplications=安装程序无法自动关闭所有应用程序。建议在继续之前关闭所有正在使用需更新文件的应用程序。
PrepareToInstallNeedsRestart=安装程序必须重启计算机。重启后请再次运行安装程序以完成 [name] 的安装。%n%n您要立即重启吗？
WizardInstalling=正在安装
InstallingLabel=正在安装 [name]，请稍候……
FinishedHeadingLabel=[name] 安装完成
FinishedLabelNoIcons=[name] 已成功安装到您的计算机。
FinishedLabel=[name] 已成功安装到您的计算机。可以通过选择已安装的快捷方式来启动应用程序。
ClickFinish=点击“完成”退出安装向导。
FinishedRestartLabel=要完成安装，安装程序需要重新启动您的计算机。现在重新启动吗？
FinishedRestartMessage=要完成 [name] 的安装，必须重新启动您的计算机。%n%n现在重新启动吗？
ShowReadmeCheck=查看自述文件
YesRadio=是，立即重新启动计算机
NoRadio=否，稍后手动重新启动计算机
RunEntryExec=运行 %1
RunEntryShellExec=查看 %1
ChangeDiskTitle=需要下一张磁盘
SelectDiskLabel2=请插入磁盘 %1 并点击“确定”。%n%n如果该磁盘上的文件可以在下面显示文件夹之外的其他文件夹中找到，请输入正确路径或点击“浏览”。
PathLabel=路径(&P):
FileNotInDir2=在“%2”中找不到文件“%1”。请插入正确的磁盘或选择其他文件夹。
SelectDirectoryLabel=请指定下一张磁盘的位置。
SetupAborted=安装未完成。%n%n请更正问题后重新运行安装程序。
AbortRetryIgnoreSelectAction=选择操作
AbortRetryIgnoreRetry=重试(&T)
AbortRetryIgnoreIgnore=忽略错误并继续(&I)
AbortRetryIgnoreCancel=取消安装
RetryCancelSelectAction=选择操作
RetryCancelRetry=重试(&T)
RetryCancelCancel=取消
StatusClosingApplications=正在关闭应用程序……
StatusCreateDirs=正在创建目录...
StatusExtractFiles=正在解压文件...
StatusDownloadFiles=Downloading files...
StatusCreateIcons=正在创建快捷方式...
StatusCreateIniEntries=正在写入 INI 文件...
StatusCreateRegistryEntries=正在写入注册表...
StatusRegisterFiles=正在注册文件...
StatusSavingUninstall=正在保存卸载信息...
StatusRunProgram=正在完成安装...
StatusRestartingApplications=正在重新启动应用程序……
StatusRollback=正在回滚更改...
ErrorInternal2=内部错误:%1
ErrorFunctionFailedNoCode=%1 失败
ErrorFunctionFailed=%1 失败；代码 %2
ErrorFunctionFailedWithMessage=%1 失败；代码 %2。%n%3
ErrorExecutingProgram=无法执行文件:%n%1
ErrorRegOpenKey=打开注册表项时出错:%n%1\%2
ErrorRegCreateKey=创建注册表项时出错:%n%1\%2
ErrorRegWriteKey=写入注册表项时出错:%n%1\%2
ErrorIniEntry=在文件“%1”中创建 INI 条目时出错。
FileAbortRetryIgnoreSkipNotRecommended=跳过此文件（不推荐）(&S)
FileAbortRetryIgnoreIgnoreNotRecommended=忽略错误并继续（不推荐）(&I)
SourceIsCorrupted=源文件已损坏
SourceDoesntExist=源文件“%1”不存在
SourceVerificationFailed=源文件验证失败:%1
VerificationSignatureDoesntExist=The signature file "%1" does not exist
VerificationSignatureInvalid=The signature file "%1" is invalid
VerificationKeyNotFound=The signature file "%1" uses an unknown key
VerificationFileNameIncorrect=The name of the file is incorrect
VerificationFileTagIncorrect=The tag of the file is incorrect
VerificationFileSizeIncorrect=The size of the file is incorrect
VerificationFileHashIncorrect=The hash of the file is incorrect
ExistingFileReadOnly2=现有文件因标记为只读而无法替换。
ExistingFileReadOnlyRetry=删除只读属性后重试(&R)
ExistingFileReadOnlyKeepExisting=保留现有文件(&K)
ErrorReadingExistingDest=尝试读取现有文件时发生错误:
FileExistsSelectAction=选择操作
FileExists2=该文件已存在。
FileExistsOverwriteExisting=覆盖现有文件(&O)
FileExistsKeepExisting=保留现有文件(&K)
FileExistsOverwriteOrKeepAll=对后续冲突执行相同操作(&D)
ExistingFileNewerSelectAction=选择操作
ExistingFileNewer2=现有文件比安装程序要安装的文件更新。
ExistingFileNewerOverwriteExisting=覆盖现有文件(&O)
ExistingFileNewerKeepExisting=保留现有文件（推荐）(&K)
ExistingFileNewerOverwriteOrKeepAll=对后续冲突执行相同操作(&D)
ErrorChangingAttr=尝试更改现有文件的属性时发生错误:
ErrorCreatingTemp=尝试在目标目录中创建文件时发生错误:
ErrorReadingSource=尝试读取源文件时发生错误:
ErrorCopying=无法复制文件 %1 到 %2%n%n%3
ErrorDownloading=尝试下载文件时发生错误:
ErrorExtracting=尝试解压压缩包时发生错误:
ErrorReplacingExistingFile=尝试替换现有文件时发生错误:
ErrorRestartReplace=RestartReplace 失败:
ErrorRenamingTemp=尝试在目标目录中重命名文件时发生错误:
ErrorRegisterServer=无法注册 DLL/OCX:%1
ErrorRegSvr32Failed=RegSvr32 失败，退出代码 %1
ErrorRegisterTypeLib=无法注册类型库:%1
UninstallDisplayNameMark=%1（%2）
UninstallDisplayNameMarks=%1（%2，%3）
UninstallDisplayNameMark32Bit=32 位
UninstallDisplayNameMark64Bit=64 位
UninstallDisplayNameMarkAllUsers=所有用户
UninstallDisplayNameMarkCurrentUser=当前用户
ErrorOpeningReadme=尝试打开自述文件时发生错误。
ErrorRestartingComputer=安装程序无法重新启动计算机，请手动重启。
UninstallNotFound=文件“%1”不存在。是否要删除该程序的卸载引用？
UninstallOpenError=无法打开文件“%1”，无法卸载
UninstallUnsupportedVer=卸载日志文件“%1”的格式无法被此版本卸载程序识别，无法卸载
UninstallUnknownEntry=遇到未知条目（%1）
ConfirmUninstall=您确定要完全移除 %1 及其所有组件吗？%n%n此操作无法撤销。
UninstallOnlyOnWin64=此安装只能在 64 位 Windows 上卸载。
OnlyAdminCanUninstall=此安装只能由具有管理员权限的用户卸载。
UninstallStatusLabel=正在从您的计算机移除 %1，请稍候。
UninstalledAll=%1 已成功从您的计算机中移除。
UninstalledMost=%1 卸载完成。%n%n部分内容无法移除，可手动删除。
UninstalledAndNeedsRestart=要完成 %1 的卸载，必须重新启动计算机。%n%n您要立即重启吗？
UninstallDataCorrupted=卸载信息文件已损坏。无法卸载。
ConfirmDeleteSharedFileTitle=删除共享文件？
ConfirmDeleteSharedFile2=系统指示以下共享文件已不再被任何程序使用。您希望卸载程序删除该共享文件吗？%n%n如果仍有程序使用该文件而它被删除，这些程序可能无法正常运行。如果不确定，请选择“否”。将文件保留在系统中不会造成任何损害。
SharedFileNameLabel=文件名:
SharedFileLocationLabel=位置:
WizardUninstalling=卸载状态
StatusUninstalling=正在卸载 %1……
ShutdownBlockReasonInstallingApp=正在安装 %1。
ShutdownBlockReasonUninstallingApp=正在卸载 %1。
[CustomMessages]
; Add your own custom messages here.
