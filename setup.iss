; AI智能助手 Inno Setup 安装脚本
; 版本 v1.0

[Setup]
; 基础应用信息
AppName=AI智能助手
AppVersion=1.0
AppPublisher=AI智能助手开发团队
AppPublisherURL=https://github.com/
AppSupportURL=https://github.com/
AppUpdatesURL=https://github.com/

; 安装配置
DefaultDirName={localappdata}\Programs\AI_GZT
DefaultGroupName=AI_GZT
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=AI_GZT_Setup_v1.0
SetupIconFile=app_icon.ico
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern

; 权限与架构
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; 卸载配置
UninstallDisplayIcon={app}\AI_GZT.exe
UninstallDisplayName=AI智能助手 v1.0
CloseApplications=yes
CloseApplicationsFilter=AI_GZT.exe

; 许可协议配置（安装向导显示第三方开源声明）
LicenseFile=THIRD_PARTY_LICENSES.md

[Languages]
Name: "chinesesimplified"; MessagesFile: "Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"; Flags: checkedonce
Name: "startupicon"; Description: "开机自动启动AI_GZT"; GroupDescription: "启动选项:"; Flags: unchecked

[Files]
; 打包所有绿色版文件
Source: "dist\AI_GZT\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; 第三方开源许可证文件（强制打包到程序根目录，合规要求）
Source: "THIRD_PARTY_LICENSES.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; 开始菜单快捷方式（自动使用exe内嵌图标，无需外部ico文件）
Name: "{group}\AI_GZT"; Filename: "{app}\AI_GZT.exe"
Name: "{group}\使用说明"; Filename: "{app}\AI_GZT_User_Guide.md"
Name: "{group}\卸载AI_GZT"; Filename: "{uninstallexe}"
; 桌面快捷方式
Name: "{autodesktop}\AI_GZT"; Filename: "{app}\AI_GZT.exe"; Tasks: desktopicon
; 开机自启快捷方式
Name: "{userstartup}\AI_GZT"; Filename: "{app}\AI_GZT.exe"; Tasks: startupicon

[Run]
; 安装完成后可选操作（显式指定工作目录避免路径异常，全版本兼容无特殊标志）
Filename: "{app}\AI_GZT.exe"; Description: "立即启动AI_GZT"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent
Filename: "explorer.exe"; Parameters: """{app}\AI_GZT_User_Guide.md"""; Description: "打开使用说明文档"; Flags: nowait postinstall skipifsilent unchecked