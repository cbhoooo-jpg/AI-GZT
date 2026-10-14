; AI智能助手（全外置依赖版） Inno Setup 安装脚本
; 版本 V2.0
; 说明:本脚本与 setup.iss 完全隔离，安装目录/开始菜单组/产物名/快捷方式均独立，可与"开箱即用版"同机共存互不覆盖

[Setup]
; 基础应用信息
AppName=AI智能助手（全外置依赖版）
AppVersion=2.0
AppPublisher=AI智能助手开发团队
AppPublisherURL=https://gitee.com/chen-bohan3000/ai-gzt
AppSupportURL=https://gitee.com/chen-bohan3000/ai-gzt
AppUpdatesURL=https://gitee.com/chen-bohan3000/ai-gzt

; 安装配置（与现有版隔离:独立安装目录、独立开始菜单组、独立产物名）
DefaultDirName={localappdata}\Programs\AI_GZT_NoDeps
DefaultGroupName=AI_GZT_NoDeps
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=AI_GZT_NoDeps_Setup_V2.0
SetupIconFile=app_icon.ico
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern

; 权限与架构
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; 卸载配置
UninstallDisplayIcon={app}\AI_GZT_NoDeps.exe
UninstallDisplayName=AI智能助手（全外置依赖版） V2.0
CloseApplications=yes
CloseApplicationsFilter=AI_GZT_NoDeps.exe

; 许可协议配置（安装向导显示第三方开源声明）
LicenseFile=THIRD_PARTY_LICENSES.md

[Languages]
Name: "chinesesimplified"; MessagesFile: "Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"; Flags: checkedonce
Name: "startupicon"; Description: "开机自动启动AI_GZT_NoDeps"; GroupDescription: "启动选项:"; Flags: unchecked

[Files]
; 打包全外置依赖版绿色包所有文件
Source: "dist\AI_GZT_NoDeps\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; 第三方开源许可证文件（强制打包到程序根目录，合规要求）
Source: "THIRD_PARTY_LICENSES.md"; DestDir: "{app}"; Flags: ignoreversion
; 项目自身 Apache 2.0 许可证（二次分发须保留版权声明与 LICENSE，合规要求）
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; 开始菜单快捷方式（自动使用exe内嵌图标，无需外部ico文件）
Name: "{group}\AI_GZT NoDeps"; Filename: "{app}\AI_GZT_NoDeps.exe"
Name: "{group}\使用说明"; Filename: "{app}\AI_GZT_User_Guide.md"
Name: "{group}\卸载AI_GZT NoDeps"; Filename: "{uninstallexe}"
; 桌面快捷方式
Name: "{autodesktop}\AI_GZT NoDeps"; Filename: "{app}\AI_GZT_NoDeps.exe"; Tasks: desktopicon
; 开机自启快捷方式
Name: "{userstartup}\AI_GZT NoDeps"; Filename: "{app}\AI_GZT_NoDeps.exe"; Tasks: startupicon

[Run]
; 安装完成后可选操作（显式指定工作目录避免路径异常，全版本兼容无特殊标志）
Filename: "{app}\AI_GZT_NoDeps.exe"; Description: "立即启动AI_GZT（全外置依赖版）"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent
Filename: "explorer.exe"; Parameters: """{app}\AI_GZT_User_Guide.md"""; Description: "打开使用说明文档"; Flags: nowait postinstall skipifsilent unchecked