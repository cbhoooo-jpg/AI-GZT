# 第三方开源组件声明与许可证
本产品（AI智能助手）使用了以下第三方开源组件、模型和工具，所有组件均遵循其对应开源许可证的要求使用，特此声明。

------------------------------------------------------------------------------

## 一、第三方组件清单

### 1. Python 核心依赖
| 组件名称 | 版本 | 许可证类型 | 版权方 |
|----------|------|------------|--------|
| PySide6 | 6.8.0.2 | LGPL v3 | The Qt Company Ltd. |
| shiboken6 | 6.8.0.2 | LGPL v3 | The Qt Company Ltd. |
| FastAPI | 0.110.0 | MIT | Sebastián Ramírez |
| starlette | 0.36.3 | BSD 3-Clause | Encode |
| uvicorn | 0.29.0 | BSD 3-Clause | Encode |
| click | 8.1.7 | BSD 3-Clause | Pallets Team |
| sse-starlette | 2.0.0 | BSD 3-Clause | sysid |
| python-multipart | 0.0.9 | Apache 2.0 | Andrew Dong |
| httpx | 0.27.0 | BSD 3-Clause | Encode |
| httpcore | 1.0.4 | BSD 3-Clause | Encode |
| h11 | 0.14.0 | MIT | Nathaniel J. Smith |
| anyio | 4.3.0 | MIT | Alex Grönholm |
| sniffio | 1.3.1 | MIT | Nathaniel J. Smith |
| certifi | 2024.2.2 | MPL 2.0 | Kenneth Reitz |
| idna | 3.6 | BSD 3-Clause | Kim Davies |
| pydantic | 2.6.4 | MIT | Samuel Colvin |
| pydantic-core | 2.16.3 | MIT | Pydantic Team |
| annotated-types | 0.6.0 | MIT | David Steele |
| typing-extensions | 4.10.0 | PSF License | Python Software Foundation |
| jiter | 0.4.0 | MIT | Pydantic Team |
| requests | 2.31.0 | Apache 2.0 | Kenneth Reitz |
| urllib3 | 2.2.1 | MIT | Andrey Petrov |
| six | 1.16.0 | MIT | Benjamin Peterson |
| pypinyin | 0.50.0 | MIT | mozillazg |
| openai | 1.35.12 | Apache 2.0 | OpenAI |
| distro | 1.9.0 | Apache 2.0 | Nir Cohen |
| tqdm | 4.66.2 | MIT | tqdm developers |
| volcengine | 1.0.0 | 火山引擎SDK许可 | 火山引擎 |
| tos | 2.1.0 | 火山引擎SDK许可 | 火山引擎 |
| newspaper3k | 0.2.8 | MIT | Lucas Ou-Yang |
| lxml | 5.1.0 | BSD 3-Clause | lxml dev team |
| beautifulsoup4 | 4.12.3 | MIT | Leonard Richardson |
| tldextract | 5.1.2 | BSD 3-Clause | John Kurkowski |
| chardet | ≥3.0.2（newspaper3k 传递依赖） | LGPL v2.1 | Daniel Blanchard |
| APScheduler | 3.10.4 | MIT | Alex Grönholm |
| pytz | 2021.3 | MIT | Stuart Bishop |
| tzlocal | 5.2 | MIT | Lennart Regebro |
| watchdog | 4.0.0 | Apache 2.0 | Yesudeep Mangalapilly |
| mss | 9.0.1 | MIT | Mickaël Schoentgen |
| screeninfo | 0.8.1 | MIT | Rhys Elsmore |
| Pillow | 10.3.0 | HPND (MIT类) | Jeffrey A. Clark et al. |
| faiss-cpu | 1.8.0 | MIT | Meta AI (Facebook Inc.) |
| torch | 2.2.2 | BSD 3-Clause | PyTorch Contributors |
| sentence-transformers | 2.6.1 | Apache 2.0 | UKP Lab |
| transformers | 4.44.2 | Apache 2.0 | Hugging Face Inc. |
| tokenizers | 0.19.1 | Apache 2.0 | Hugging Face Inc. |
| huggingface-hub | 0.23.2 | Apache 2.0 | Hugging Face Inc. |
| safetensors | 0.4.2 | Apache 2.0 | Hugging Face Inc. |
| regex | 2023.12.25 | Apache 2.0 | Matthew Barnett |
| sentencepiece | 0.2.2 | Apache 2.0 | Google |
| numpy | 1.26.4 | BSD 3-Clause | NumPy Developers |
| pyinstaller | 6.5.0 | GPL v2 + 链接例外 | PyInstaller Development Team |
| pywin32-ctypes | 0.2.2 | BSD 3-Clause | Enthought Inc. |
| pefile | 2023.2.7 | MIT | Ero Carrera |
| psutil | ≥5.9.0（构建环境实测 7.2.2） | BSD 3-Clause | Giampaolo Rodola |

**插件可选依赖（默认不随安装包分发，用户使用文件转换插件对应功能时按提示自行安装）:**

| 组件名称 | 约定版本 | 许可证类型 | 版权方 |
|----------|----------|------------|--------|
| openpyxl | ≥3.1.2 | MIT | Eric Gazoni |
| python-docx | ≥1.1.0 | MIT | Steve Canny |
| pypandoc | ≥1.13 | GPL v2 | Jessica Tegner（运行时另需外部 pandoc，同为 GPL v2） |

> 版本核对说明:① 上表直接依赖版本号以项目根目录 `requirements.txt` 的锁定版本为准；间接传递依赖（如 newspaper3k 生态的 chardet/soupsieve/nltk、transformers 生态的 tokenizers/safetensors 等）版本随锁定环境，许可证均为 MIT/Apache/BSD 类宽松许可；② openpyxl、python-docx、pypandoc 仅被文件转换插件在执行对应功能时延迟导入，不随安装包默认分发；其中 pypandoc 及其调用的 pandoc 为 GPL v2 许可，因默认不分发、仅在用户主动安装启用时运行，不构成对主程序的许可传染；③ 本产品不包含 edge-tts、pandas、python-pptx、PyAudio、pydub、pyperclip、cryptography、loguru、PyYAML 等组件。

### 2. 前端静态资源（static目录）
| 组件名称 | 版本 | 许可证类型 | 版权方 |
|----------|------|------------|--------|
| Vue.js | 2.x | MIT | Evan You |
| Element UI | 2.x | MIT | ElemeFE |
| Axios | 1.x | MIT | Matt Zabriskie |
| CodeMirror | 5.x | MIT | Marijn Haverbeke |
| highlight.js | 11.x | BSD 3-Clause | Ivan Sagalaev |
| SheetJS (xlsx) | 0.18.x | Apache 2.0 | SheetJS LLC |
| docx-preview | 0.3.x | MIT | Volodymyr Baydalka |
| element-icons 字体 | - | MIT | ElemeFE |

### 3. 人工智能模型
| 模型名称 | 版本 | 许可证类型 | 版权方 |
|----------|------|------------|--------|
| gte-small-zh | - | Apache 2.0 | 阿里巴巴达摩院 (thenlper) |

### 4. 打包与构建工具
| 工具名称 | 版本 | 许可证类型 | 版权方 |
|----------|------|------------|--------|
| PyInstaller | 6.x | GPL v2 + 链接例外 | PyInstaller Development Team |
| Inno Setup | 6.7.x | Inno Setup License (免费商用) | Jordan Russell |
| Python | 3.11.x | PSF License | Python Software Foundation |

------------------------------------------------------------------------------

## 二、许可证合规说明

### 1. PySide6/Qt LGPL v3 合规声明
本产品动态链接使用了PySide6（Qt for Python），遵循GNU Lesser General Public License v3.0（LGPL v3）许可证要求:
- ✅ 本产品自有业务代码独立于Qt库，不与Qt静态链接，用户可自行替换`_internal/PySide6`目录下的Qt库文件为修改后的版本
- ✅ 本产品未对Qt/PySide6源代码进行任何修改
- ✅ 随产品完整附带LGPL v3许可证文本
- ✅ 源代码获取承诺:用户可通过以下渠道获取对应版本PySide6/Qt的完整源代码:
  1. 官方Qt下载地址:https://download.qt.io/archive/qt/
  2. PySide6官方仓库:https://code.qt.io/pyside/pyside-setup/
  3. 如需获取本产品使用的对应版本源代码，可联系开发者免费获取，仅收取介质和邮寄成本费用。

### 2. MIT/BSD类许可证说明
所有采用MIT、BSD类许可证的组件，均允许商业使用、修改、分发，合规要求仅为保留原始版权声明和许可证文本，本产品已完整保留相关声明。

### 3. Apache 2.0 许可证说明
所有采用Apache 2.0许可证的组件、模型，均允许商业使用、修改、分发，合规要求为保留许可证文本、注明原作者、声明修改内容（本产品未对相关组件做修改）。

------------------------------------------------------------------------------

## 三、完整许可证文本
### MIT 许可证（MIT License）
Copyright (c) [对应年份] [版权持有人]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

------------------------------------------------------------------------------

### Apache 许可证 2.0（Apache License 2.0）
Version 2.0, January 2004
http://www.apache.org/licenses/

TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

1. Definitions.
"License" shall mean the terms and conditions for use, reproduction,
and distribution as defined by Sections 1 through 9 of this document.
"Licensor" shall mean the copyright owner or entity authorized by
the copyright owner that is granting the License.
"Legal Entity" shall mean the union of the acting entity and all
other entities that control, are controlled by, or are under common
control with that entity. For the purposes of this definition,
"control" means (i) the power, direct or indirect, to cause the
direction or management of such entity, whether by contract or
otherwise, or (ii) ownership of fifty percent (50%) or more of the
outstanding shares, or (iii) beneficial ownership of such entity.
"You" (or "Your") shall mean an individual or Legal Entity
exercising permissions granted by this License.
"Source" form shall mean the preferred form for making modifications,
including but not limited to software source code, documentation
source, and configuration files.
"Object" form shall mean any form resulting from mechanical
transformation or translation of a Source form, including but
not limited to compiled object code, generated documentation,
and conversions to other media types.
"Work" shall mean the work of authorship, whether in Source or
Object form, made available under the License, as indicated by a
copyright notice that is included in or attached to the work
(an example is provided in the Appendix below).
"Derivative Works" shall mean any work, whether in Source or Object
form, that is based on (or derived from) the Work and for which the
editorial revisions, annotations, elaborations, or other modifications
represent, as a whole, an original work of authorship. For the purposes
of this License, Derivative Works shall not include works that remain
separable from, or merely link (or bind by name) to the interfaces of,
the Work and Derivative Works thereof.
"Contribution" shall mean any work of authorship, including
the original version of the Work and any modifications or additions
to that Work or Derivative Works thereof, that is intentionally
submitted to Licensor for inclusion in the Work by the copyright owner
or by an individual or Legal Entity authorized to submit on behalf of
the copyright owner. For the purposes of this definition, "submitted"
means any form of electronic, verbal, or written communication sent
to the Licensor or its representatives, including but not limited to
communication on electronic mailing lists, source code control systems,
and issue tracking systems that are managed by, or on behalf of, the
Licensor for the purpose of discussing and improving the Work, but
excluding communication that is conspicuously marked or otherwise
designated in writing by the copyright owner as "Not a Contribution."
"Contributor" shall mean Licensor and any individual or Legal Entity
on behalf of whom a Contribution has been received by Licensor and
subsequently incorporated within the Work.

2. Grant of Copyright License. Subject to the terms and conditions of
this License, each Contributor hereby grants to You a perpetual,
worldwide, non-exclusive, no-charge, royalty-free, irrevocable
copyright license to reproduce, prepare Derivative Works of,
publicly display, publicly perform, sublicense, and distribute the
Work and such Derivative Works in Source or Object form.

3. Grant of Patent License. Subject to the terms and conditions of
this License, each Contributor hereby grants to You a perpetual,
worldwide, non-exclusive, no-charge, royalty-free, irrevocable
(except as stated in this section) patent license to make, have made,
use, offer to sell, sell, import, and otherwise transfer the Work,
where such license applies only to those patent claims licensable
by such Contributor that are necessarily infringed by their
Contribution(s) alone or by combination of their Contribution(s)
with the Work to which such Contribution(s) was submitted. If You
institute patent litigation against any entity (including a
cross-claim or counterclaim in a lawsuit) alleging that the Work
or a Contribution incorporated within the Work constitutes direct
or contributory patent infringement, then any patent licenses
granted to You under this License for that Work shall terminate
as of the date such litigation is filed.

4. Redistribution. You may reproduce and distribute copies of the
Work or Derivative Works thereof in any medium, with or without
modifications, and in Source or Object form, provided that You
meet the following conditions:
(a) You must give any other recipients of the Work or Derivative Works a copy of this License; and
(b) You must cause any modified files to carry prominent notices stating that You changed the files; and
(c) You must retain, in the Source form of any Derivative Works that You distribute, all copyright, patent, trademark, and attribution notices from the Source form of the Work, excluding those notices that do not pertain to any part of the Derivative Works; and
(d) If the Work includes a "NOTICE" text file as part of its distribution, then any Derivative Works that You distribute must include a readable copy of the attribution notices contained within such NOTICE file, excluding those notices that do not pertain to any part of the Derivative Works, in at least one of the following places: within a NOTICE text file distributed as part of the Derivative Works; within the Source form or documentation, if provided along with the Derivative Works; or, within a display generated by the Derivative Works, if and wherever such third-party notices normally appear. The contents of the NOTICE file are for informational purposes only and do not modify the License. You may add Your own attribution notices within Derivative Works that You distribute, alongside or as an addendum to the NOTICE text from the Work, provided that such additional attribution notices cannot be construed as modifying the License.
You may add Your own copyright statement to Your modifications and may provide additional or different license terms and conditions for use, reproduction, or distribution of Your modifications, or for any such Derivative Works as a whole, provided Your use, reproduction, and distribution of the Work otherwise complies with the conditions stated in this License.

5. Submission of Contributions. Unless You explicitly state otherwise,
any Contribution intentionally submitted for inclusion in the Work by You to the Licensor shall be under the terms and conditions of this License, without any additional terms or conditions. Notwithstanding the above, nothing herein shall supersede or modify the terms of any separate license agreement you may have executed with Licensor regarding such Contributions.

6. Trademarks. This License does not grant permission to use the trade
names, trademarks, service marks, or product names of the Licensor, except as required for reasonable and customary use in describing the origin of the Work and reproducing the content of the NOTICE file.

7. Disclaimer of Warranty. Unless required by applicable law or
agreed to in writing, Licensor provides the Work (and each Contributor provides its Contributions) on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied, including, without limitation, any warranties or conditions of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A PARTICULAR PURPOSE. You are solely responsible for determining the appropriateness of using or redistributing the Work and assume any risks associated with Your exercise of permissions under this License.

8. Limitation of Liability. In no event and under no legal theory,
whether in tort (including negligence), contract, or otherwise, unless required by applicable law (such as deliberate and grossly negligent acts) or agreed to in writing, shall any Contributor be liable to You for damages, including any direct, indirect, special, incidental, or consequential damages of any character arising as a result of this License or out of the use or inability to use the Work (including but not limited to damages for loss of goodwill, work stoppage, computer failure or malfunction, or any and all other commercial damages or losses), even if such Contributor has been advised of the possibility of such damages.

9. Accepting Warranty or Additional Liability. While redistributing
the Work or Derivative Works thereof, You may choose to offer, and charge a fee for, acceptance of support, warranty, indemnity, or other liability obligations and/or rights consistent with this License. However, in accepting such obligations, You may act only on Your own behalf and on Your sole responsibility, not on behalf of any other Contributor, and only if You agree to indemnify, defend, and hold each Contributor harmless for any liability incurred by, or claims asserted against, such Contributor by reason of your accepting any such warranty or additional liability.

END OF TERMS AND CONDITIONS

------------------------------------------------------------------------------

### BSD 3-Clause 许可证（BSD 3-Clause License）
Copyright (c) [对应年份], [版权持有人]
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

------------------------------------------------------------------------------

### GNU Lesser General Public License v3.0（LGPL v3）
GNU LESSER GENERAL PUBLIC LICENSE
Version 3, 29 June 2007

Copyright (C) 2007 Free Software Foundation, Inc. <https://fsf.org/>
Everyone is permitted to copy and distribute verbatim copies of this license document, but changing it is not allowed.

This version of the GNU Lesser General Public License incorporates the terms and conditions of version 3 of the GNU General Public License, supplemented by the additional permissions listed below.

0. Additional Definitions.
As used herein, "this License" refers to version 3 of the GNU Lesser General Public License, and the "GNU GPL" refers to version 3 of the GNU General Public License.
"The Library" refers to a covered work governed by this License, other than an Application or a Combined Work as defined below.
An "Application" is any work that makes use of an interface provided by the Library, but which is not otherwise based on the Library. Defining a subclass of a class defined by the Library is deemed a mode of using an interface provided by the Library.
A "Combined Work" is a work produced by combining or linking an Application with the Library. The particular version of the Library with which the Combined Work was made is also called the "Linked Version".
The "Minimal Corresponding Source" for a Combined Work means the Corresponding Source for the Combined Work, excluding any source code for portions of the Combined Work that, considered in isolation, are based on the Application, and not on the Linked Version.
The "Corresponding Application Code" for a Combined Work means the object code and/or source code for the Application, including any data and utility programs needed for reproducing the Combined Work from the Application, but excluding the System Libraries of the Combined Work.

1. Exception to Section 3 of the GNU GPL.
You may convey a covered work under Sections 3 and 4 of this License, without being bound by Section 3 of the GNU GPL.

2. Conveying Modified Versions.
If you modify a copy of the Library, and, in your modifications, a facility refers to a function or data to be supplied by an Application that uses the facility (other than as an argument passed when the facility is invoked), then you may convey a copy of the modified version:
a) under this License, provided that you make a good faith effort to ensure that, in the event an Application does not supply the function or data, the facility still operates, and performs whatever part of its purpose remains meaningful, or
b) under the GNU GPL, with none of the additional permissions of this License applicable to that copy.

3. Object Code Incorporating Material from Library Header Files.
The object code form of an Application may incorporate material from a header file that is part of the Library. You may convey such object code under terms of your choice, provided that, if the incorporated material is not limited to numerical parameters, data structure layouts and accessors, or small macros, inline functions and templates (ten or fewer lines in length), you do both of the following:
a) Give prominent notice with each copy of the object code that the Library is used in it and that the Library and its use are covered by this License.
b) Accompany the object code with a copy of the GNU GPL and this license document.

4. Combined Works.
You may convey a Combined Work under terms of your choice that, taken together, effectively do not restrict modification of the portions of the Library contained in the Combined Work and reverse engineering for debugging such modifications, if you also do each of the following:
a) Give prominent notice with each copy of the Combined Work that the Library is used in it and that the Library and its use are covered by this License.
b) Accompany the Combined Work with a copy of the GNU GPL and this license document.
c) For a Combined Work that displays copyright notices during execution, include the copyright notice for the Library among these notices, as well as a reference directing the user to the copies of the GNU GPL and this license document.
d) Do one of the following:
   0) Convey the Minimal Corresponding Source under the terms of this License, and the Corresponding Application Code in a form suitable for, and under terms that permit, the user to recombine or relink the Application with a modified version of the Linked Version to produce a modified Combined Work, in the manner specified by Section 6 of the GNU GPL for conveying Corresponding Source.
   1) Use a suitable shared library mechanism for linking with the Library. A suitable mechanism is one that (a) uses at run time a copy of the Library already present on the user's computer system, and (b) will operate properly with a modified version of the Library that is interface-compatible with the Linked Version.
e) Provide Installation Information, but only if you would otherwise be required to provide such information under Section 6 of the GNU GPL, and only to the extent that such information is necessary to install and execute a modified version of the Combined Work produced by recombining or relinking the Application with a modified version of the Linked Version. (If you use option 4d0, the Installation Information must accompany the Minimal Corresponding Source and Corresponding Application Code. If you use option 4d1, you must provide the Installation Information in the manner specified by Section 6 of the GNU GPL for conveying Corresponding Source.)

5. Combined Libraries.
You may place library facilities that are a work based on the Library side by side in a single library together with other library facilities that are not Applications and are not covered by this License, and convey such a combined library under terms of your choice, if you do both of the following:
a) Accompany the combined library with a copy of the same work based on the Library, uncombined with any other library facilities, conveyed under the terms of this License.
b) Give prominent notice with the combined library that part of it is a work based on the Library, and explaining where to find the accompanying uncombined form of the same work.

6. Revised Versions of the GNU Lesser General Public License.
The Free Software Foundation may publish revised and/or new versions of the GNU Lesser General Public License from time to time. Such new versions will be similar in spirit to the present version, but may differ in detail to address new problems or concerns.
Each version is given a distinguishing version number. If the Library as you received it specifies that a certain numbered version of the GNU Lesser General Public License "or any later version" applies to it, you have the option of following the terms and conditions either of that published version or of any later version published by the Free Software Foundation. If the Library as you received it does not specify a version number of the GNU Lesser General Public License, you may choose any version of the GNU Lesser General Public License ever published by the Free Software Foundation.
If the Library as you received it specifies that a proxy can decide whether future versions of the GNU Lesser General Public License shall apply, that proxy's public statement of acceptance of any version is permanent authorization for you to choose that version for the Library.

------------------------------------------------------------------------------

### PyInstaller 许可证例外说明
PyInstaller采用GPL v2许可证，但附带特殊链接例外条款:
> As a special exception, the copyright holders of PyInstaller give you permission to combine PyInstaller with free software programs or libraries that are released under the GNU LGPL and with code included in the standard release of Python under the Python License. You may copy and distribute such a system following the terms of the GNU GPL for PyInstaller and the licenses of the other code concerned.
该例外明确允许使用PyInstaller打包非GPL许可的商业软件，你的自有代码不需要开源，无GPL传染风险。

------------------------------------------------------------------------------

### Inno Setup 许可证
Inno Setup Copyright (C) 1997-2024 Jordan Russell. All rights reserved.
Portions Copyright (C) 2000-2024 Martijn Laan. All rights reserved.
matplotlib software is Copyright (C) 2000-2024 Matplotlib Development Team. All rights reserved.

Inno Setup is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.

Inno Setup is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

In addition, as a special exception, the copyright holders of Inno Setup give permission to link the code of portions of this program with the OpenSSL library under certain conditions as described in each individual source file, and distribute linked combinations including the two.

You should have received a copy of the GNU General Public License along with Inno Setup; if not, write to the Free Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110, USA.

------------------------------------------------------------------------------

### Python 软件基金会许可证（PSF）
PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2
--------------------------------------------

1. This LICENSE AGREEMENT is between the Python Software Foundation ("PSF"), and the Individual or Organization ("Licensee") accessing and otherwise using this software ("Python") in source or binary form and its associated documentation.

2. Subject to the terms and conditions of this License Agreement, PSF hereby grants Licensee a nonexclusive, royalty-free, world-wide license to reproduce, analyze, test, perform and/or display publicly, prepare derivative works, distribute, and otherwise use Python alone or in any derivative version, provided, however, that PSF's License Agreement and PSF's notice of copyright, i.e., "Copyright (c) 2001-2024 Python Software Foundation; All Rights Reserved" are retained in Python alone or in any derivative version prepared by Licensee.

3. In the event Licensee prepares a derivative work that is based on or incorporates Python or any part thereof, and wants to make the derivative work available to others as provided herein, then Licensee hereby agrees to include in any such work a brief summary of the changes made to Python.

4. PSF is making Python available to Licensee on an "AS IS" basis. PSF MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR IMPLIED. BY WAY OF EXAMPLE, BUT NOT LIMITATION, PSF MAKES NO AND DISCLAIMS ANY REPRESENTATION OR WARRANTY OF MERCHANTABILITY OR FITNESS FOR ANY PARTICULAR PURPOSE OR THAT THE USE OF PYTHON WILL NOT INFRINGE ANY THIRD PARTY RIGHTS.

5. PSF SHALL NOT BE LIABLE TO LICENSEE OR ANY OTHER USERS OF PYTHON FOR ANY INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES OR LOSS AS A RESULT OF MODIFYING, DISTRIBUTING, OR OTHERWISE USING PYTHON, OR ANY DERIVATIVE THEREOF, EVEN IF ADVISED OF THE POSSIBILITY THEREOF.

6. This License Agreement will automatically terminate upon a material breach of its terms and conditions.

7. Nothing in this License Agreement shall be deemed to create any relationship of agency, partnership, or joint venture between PSF and Licensee. This License Agreement does not grant permission to use PSF trademarks or trade name in a product name or product endorsement, except as required for reasonable and customary use in describing the origin of Python.