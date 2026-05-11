# 藏语→中文实时翻译工具 代码审查报告

**仓库：** `MinjiaShen/tibetan-chinese-translator`  
**审查版本：** v2.1（2026-05-09）  
**审查日期：** 2026-05-11  
**审查范围：** 全量文件（1,998 行，7 个源文件）  
**测试执行：** 94 项单元测试全部通过（`unittest`，运行耗时 3.11s）

---

## 目录

1. [项目概览](#1-项目概览)
2. [架构评估](#2-架构评估)
3. [已发现的 Bug](#3-已发现的-bug)
4. [改进与优化建议](#4-改进与优化建议)
5. [功能扩展请求](#5-功能扩展请求)
6. [测试体系评估](#6-测试体系评估)
7. [文档问题](#7-文档问题)
8. [汇总矩阵](#8-汇总矩阵)
9. [优先级路线图](#9-优先级路线图)

---

## 1. 项目概览

### 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `tibetan-translator.py` | 678 | 核心：内嵌 HTML + Python HTTP 服务器 |
| `index.html` | 481 | 独立 HTML（与内嵌版本并行维护） |
| `install.sh` | 118 | macOS/Linux 一键安装脚本 |
| `start.command` | 4 | macOS 双击启动脚本 |
| `启动翻译.bat` | 4 | Windows 双击启动脚本 |
| `test_server.py` | 276 | Python HTTP 服务器单元测试 |
| `test_js_logic.py` | 189 | JavaScript 静态分析测试 |
| `test_html.py` | 182 | HTML 结构完整性测试 |
| `test_install.py` | 74 | `install.sh` 脚本测试 |

### 技术栈

| 层次 | 技术 | 备注 |
|------|------|------|
| 运行时 | Python 3.8+ 标准库 | 零第三方依赖 |
| 前端 | 原生 HTML/CSS/ES2020 | 内嵌于 Python 字符串 |
| 语音识别 | Web Speech API | 仅 Chrome/Edge 支持 |
| OCR | Tesseract.js v5（CDN 延迟加载） | 客户端处理，首次约 1MB |
| 翻译 | Google Translate 非官方端点 | `client=gtx` 私有参数 |
| HTTP 服务 | `socketserver.TCPServer` 子类 | 单线程请求处理 |

---

## 2. 架构评估

### 优势

- **零依赖分发**设计合理，Python 标准库足以支撑服务端职责，大幅降低用户安装门槛。
- **翻译队列版本号机制**（`qVersion`）是处理标签页切换并发问题的精巧设计，体现了对浏览器异步模型的深刻理解。
- **Tesseract.js 延迟加载**避免了首屏阻塞，对慢速网络用户体验友好。
- **`ReusableTCPServer` 的 `allow_reuse_address` 前置设置**正确修复了 `socketserver.TCPServer` 的已知时序缺陷。
- 测试覆盖率在同类单文件工具中属于较高水平，静态分析思路务实。

### 结构性风险

**最核心的架构风险**是对 `translate.googleapis.com/translate_a/single?client=gtx` 私有端点的强依赖（见 [I-1](#i-1-google-translate-私有端点依赖架构层面风险)）。该端点是 Google Translate 网页版的内部接口，从未开放给开发者，历史上曾多次变更或封禁特定 IP 段。项目的全部翻译功能建立于此单点之上，是首要技术债务。

**第二个结构性问题**是 `tibetan-translator.py` 内嵌 HTML 与 `index.html` 的双轨维护模式（见 [B-5](#b-5-内嵌-html-与-indexhtml-双轨维护版本漂移风险)）。v2.1 更新日志中已出现 `修复 index.html 同步所有修复` 的字样，说明该风险已经发生过一次，是持续存在的工程债务。

---

## 3. 已发现的 Bug

### B-1：`translateGoogle` 中 `clearTimeout` 在异常路径下重复调用

**位置：** `tibetan-translator.py`，第 307、314 行（JavaScript 内嵌段）  
**严重程度：** 低（冗余，无功能影响）

**问题代码：**

```javascript
// translateGoogle() 内的 catch + finally 块
} catch (e) {
    clearTimeout(timer);     // ← 第 307 行：catch 路径下第一次清理
    if (attempt < maxRetries - 1) {
        await new Promise(r => setTimeout(r, 1000));
        continue;
    }
    throw e;
} finally {
    clearTimeout(timer);     // ← 第 314 行：finally 路径下第二次清理（冗余）
}
```

**分析：** `clearTimeout` 对已清除的 timer ID 调用是幂等的，不会引发错误，但在重试循环（`maxRetries = 2`）中，正常请求路径的 `finally` 已足够，`catch` 块内的调用属于冗余代码。这种模式也可能混淆后续维护者对超时控制逻辑的理解。

**建议修复：**

```javascript
try {
    const r = await fetch(url, { signal: controller.signal });
    // ...
} catch (e) {
    if (attempt < maxRetries - 1) {
        await new Promise(r => setTimeout(r, 1000));
        continue;
    }
    throw e;
} finally {
    clearTimeout(timer);  // 仅在 finally 中调用一次
}
```

---

### B-2：`find_port()` 端口全部耗尽时静默回退导致服务崩溃

**位置：** `tibetan-translator.py`，第 581–590 行（Python）  
**严重程度：** 高（服务无法启动，无友好提示）

**问题代码：**

```python
def find_port(start=9090):
    for p in range(start, start + 20):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', p))
                return p
        except OSError:
            continue
    return start  # ← 关键问题：9090–9109 全部被占用时，静默返回 9090
```

**分析：** 当 9090–9109 端口全部处于占用状态时，函数返回起始值 `9090`，随后 `main()` 中的 `ReusableTCPServer(('127.0.0.1', 9090), Handler)` 必然抛出 `OSError: [Errno 98] Address already in use`。该异常未被捕获，程序直接崩溃，用户仅看到 Python 的原始堆栈跟踪，没有任何指导性错误信息。

**建议修复：**

```python
def find_port(start=9090, max_tries=20):
    for p in range(start, start + max_tries):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', p))
                return p
        except OSError:
            continue
    raise RuntimeError(
        f"端口 {start}–{start + max_tries - 1} 均已被占用，"
        f"请关闭占用这些端口的程序后重试，或使用 --port 参数指定其他端口。"
    )
```

---

### B-3：`SpeechRecognitionError` 仅处理 2 种错误码，其余静默丢失

**位置：** `tibetan-translator.py`，第 379–382 行（JavaScript 内嵌段）  
**严重程度：** 中（用户体验，语音功能核心路径）

**问题代码：**

```javascript
r.onerror = (e) => {
    if (e.error === 'not-allowed') {
        ts('❌ 请允许麦克风权限'); ss('err', '麦克风被拒绝'); stopRec();
    } else if (e.error === 'network') {
        ts('⚠️ 网络错误'); ss('err', '网络错误');
    }
    // 其余错误码完全被吞没，用户无任何反馈
};
```

**分析：** [W3C Web Speech API 规范](https://wicg.github.io/speech-api/#speechrecognitionerrorcode-enum) 定义了 8 种错误码，当前实现仅处理 `not-allowed` 和 `network`，以下情况均无任何用户提示：

| 错误码 | 触发场景 |
|--------|----------|
| `no-speech` | 超时未检测到语音输入 |
| `aborted` | 识别被中止 |
| `audio-capture` | 麦克风硬件异常 |
| `service-not-allowed` | 非 HTTPS 环境下禁用语音识别 |
| `bad-grammar` | 语法规则错误 |
| `language-not-supported` | 语言代码不受支持 |

`no-speech` 是实际使用中最常见的错误，用户长时间无声后识别器静默停止，缺少提示会使用户误以为程序卡死。

**建议修复：**

```javascript
r.onerror = (e) => {
    const messages = {
        'not-allowed':        ['❌ 请允许麦克风权限', '麦克风被拒绝'],
        'network':            ['⚠️ 网络错误，语音识别需要网络', '网络错误'],
        'no-speech':          ['🔇 未检测到语音，请靠近麦克风说话', '未检测到语音'],
        'audio-capture':      ['❌ 麦克风无法访问，请检查硬件', '音频设备错误'],
        'service-not-allowed':['❌ 语音识别服务不可用', '服务不可用'],
        'aborted':            ['⏹️ 语音识别已中止', '已中止'],
    };
    const [toast, status] = messages[e.error] || [`⚠️ 语音错误: ${e.error}`, '识别错误'];
    ts(toast);
    ss('err', status);
    if (e.error === 'not-allowed') stopRec();
};
```

---

### B-4：`ensureTesseract()` 存在并发加载竞态条件

**位置：** `tibetan-translator.py`，第 439–448 行（JavaScript 内嵌段）  
**严重程度：** 中（OCR 功能不稳定，首次使用场景）

**问题代码：**

```javascript
async function ensureTesseract() {
    if (tesseractLoaded && typeof Tesseract !== 'undefined') return true;
    // ↑ 若用户在加载期间快速触发两次（如双击按钮），
    //   两次调用均可通过此检查，导致 <script> 标签被注入两次
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js';
        script.onload = () => { tesseractLoaded = true; resolve(true); };
        script.onerror = () => reject(new Error('OCR 引擎加载失败，请检查网络'));
        document.head.appendChild(script);
    });
}
```

**分析：** 两次注入同一 CDN 脚本会导致 Tesseract 全局对象被重复初始化，内部 Worker 池可能出现状态混乱，引发不可预期的 OCR 失败或内存泄漏。虽然 `ob.disabled = true` 在 `doO()` 入口处已禁用按钮，但通过其他路径（如编程触发）仍可绕过。

**建议修复（Promise 单例锁）：**

```javascript
let _tesseractLoadPromise = null;

async function ensureTesseract() {
    if (tesseractLoaded && typeof Tesseract !== 'undefined') return true;
    if (_tesseractLoadPromise) return _tesseractLoadPromise;  // 复用进行中的加载
    _tesseractLoadPromise = new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js';
        script.onload = () => { tesseractLoaded = true; resolve(true); };
        script.onerror = (err) => {
            _tesseractLoadPromise = null;  // 失败时清除，允许重试
            reject(new Error('OCR 引擎加载失败，请检查网络'));
        };
        document.head.appendChild(script);
    });
    return _tesseractLoadPromise;
}
```

---

### B-5：内嵌 HTML 与 `index.html` 双轨维护，版本漂移风险

**位置：** `tibetan-translator.py` 第 27 行注释；`index.html`（全文）  
**严重程度：** 中（持续存在的工程债务，已发生过一次同步遗漏）

**问题证据：**

```python
# tibetan-translator.py 第 27 行（v2.1 更新日志）
- 修复 index.html 同步所有修复
```

这条注释本身就是问题的直接证据——开发者已经历过一次 `index.html` 未同步修复的情况，说明双轨维护模式在实践中已产生了 Bug。

**现状：** 两个文件虽然当前 ID 数量一致（`test_html.py` 的 `test_both_have_same_id_count` 通过），但该测试仅比对 ID 数量，无法检测 JavaScript 逻辑差异、CSS 规则变更或任何非 ID 属性的内容差异。

**建议方案：**

选项 A（推荐）：在 `test_html.py` 中增加关键 JavaScript 函数签名的一致性比对测试，将版本漂移暴露在 CI 层面。

选项 B（长期）：以 `index.html` 作为单一来源（Source of Truth），在 `tibetan-translator.py` 启动时动态读取该文件，彻底消除冗余：

```python
HTML_PATH = os.path.join(os.path.dirname(__file__), 'index.html')
with open(HTML_PATH, 'r', encoding='utf-8') as f:
    HTML = f.read()
```

此方案打破了「单文件分发」设计，需权衡。

---

### B-6：`do_HEAD` 与 `do_GET` 重复编码 HTML，且版本注释存在内部矛盾

**位置：** `tibetan-translator.py`，第 561 行、第 571 行（Python）  
**严重程度：** 低（性能浪费 + 版本注释误导）

**问题代码：**

```python
# do_GET（第 561 行）
body = HTML.encode('utf-8')   # 每次 GET 请求均重新编码

# do_HEAD（第 571 行）  
body = HTML.encode('utf-8')   # 每次 HEAD 请求均重新编码

# 另外：代码注释存在内部矛盾
# 第 330 行注释：// v2.2: 修复并发竞态
# 第 599 行 print：v2.1（UI 版本号）
# 第 177 行 HTML footer：桌面版 v2.1
```

`HTML` 是模块级字符串常量，其 UTF-8 编码结果在进程生命周期内不会改变，每次请求重新调用 `encode()` 是不必要的。同时，内部注释中出现了 `v2.2` 字样（第 330 行），但所有用户可见的版本号均显示 `v2.1`，造成版本号的内部混乱。

**建议修复：**

```python
# 模块级预计算，只编码一次
_HTML_BYTES = HTML.encode('utf-8')

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        # ...
        self.send_header('Content-Length', len(_HTML_BYTES))
        self.end_headers()
        self.wfile.write(_HTML_BYTES)

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(_HTML_BYTES))
        self.end_headers()
```

---

### B-7：空格键快捷键在键盘导航场景下行为不可靠

**位置：** `tibetan-translator.py`，第 407–409 行（JavaScript 内嵌段）  
**严重程度：** 低（无障碍访问，边缘场景）

**问题代码：**

```javascript
document.addEventListener('keydown', e => {
    if (e.code === 'Space' && !e.repeat && e.target === document.body) {
        e.preventDefault(); toggleRec();
    }
});
```

**分析：** `e.target === document.body` 在以下场景下失效：

1. 用户通过 Tab 键将焦点移至标签页切换按钮（`<button class="t">`）后，按下空格键会同时触发录音切换和按钮点击。
2. 当焦点在 `textarea` 中时，虽然 `textarea` 的 keydown 事件会先触发，但 `document.addEventListener` 的捕获机制在某些浏览器版本中仍会处理该事件。
3. 自定义屏幕阅读器快捷键可能与此冲突。

**建议修复：**

```javascript
document.addEventListener('keydown', e => {
    const activeTag = document.activeElement?.tagName;
    const isInteractive = ['INPUT', 'TEXTAREA', 'BUTTON', 'SELECT', 'A'].includes(activeTag);
    if (e.code === 'Space' && !e.repeat && !isInteractive) {
        e.preventDefault();
        toggleRec();
    }
});
```

---

## 4. 改进与优化建议

### I-1：Google Translate 私有端点依赖（架构层面风险）

**位置：** `tibetan-translator.py`，第 299 行（JavaScript 内嵌段）  
**优先级：** 极高

**问题代码：**

```javascript
const r = await fetch(
    `https://translate.googleapis.com/translate_a/single?client=gtx&sl=bo&tl=zh-CN&dt=t&q=${encodeURIComponent(text)}`,
    { signal: controller.signal }
);
```

**分析：** `client=gtx` 是 Google Translate 网页客户端的内部标识符，该接口从未出现在任何 Google 官方 API 文档中。使用此端点面临以下风险：

- Google 可能随时变更端点 URL、参数格式或响应结构，且不会提前通知。
- 高频调用会触发 IP 级别的临时封禁（Rate Limiting），README 中已承认此问题但未给出解决方案。
- 在中国大陆等部分地区，`translate.googleapis.com` 本身可能无法访问。
- 该端点不提供任何 SLA 保障。

**建议方案：**

**短期（低成本）：** 增加官方 Google Cloud Translation API 支持（用户自行提供免费额度内的 API Key），以环境变量或配置文件方式注入：

```javascript
const GOOGLE_API_KEY = window.__GOOGLE_API_KEY__ || null;
const url = GOOGLE_API_KEY
    ? `https://translation.googleapis.com/language/translate/v2?key=${GOOGLE_API_KEY}`
    : `https://translate.googleapis.com/translate_a/single?client=gtx&sl=bo&tl=zh-CN&dt=t&q=${encodeURIComponent(text)}`;
```

**中期：** 集成 [LibreTranslate](https://libretranslate.com/)（开源，支持自部署）作为备用引擎，实现引擎自动故障转移。

---

### I-2：翻译缓存缺乏真正的 LRU 淘汰策略

**位置：** `tibetan-translator.py`，第 209–210 行（JavaScript 内嵌段）  
**优先级：** 低

**问题代码：**

```javascript
// saveCache() 中
const entries = Array.from(tc.entries());
const toSave = entries.slice(-CACHE_MAX);  // 保留最近插入的 500 条
```

**分析：** ES6 `Map` 的迭代顺序是**插入顺序**，而非访问频率顺序。当前策略保留的是最近**插入**的条目，而非最近**使用**的条目。对于高频复查同一藏文词条的场景（如学术研究），早期插入的高频词可能被低频新词挤出缓存。

**建议修复（LRU 实现）：**

```javascript
function lruGet(key) {
    if (!tc.has(key)) return undefined;
    const value = tc.get(key);
    tc.delete(key);  // 删除旧位置
    tc.set(key, value);  // 重新插入，移至 Map 末尾（最近使用）
    return value;
}
```

同时在 `translate()` 中将 `tc.get(key)` 替换为 `lruGet(key)`。

---

### I-3：键盘模式缺乏大文本分段处理，长藏文请求可能静默失败

**位置：** `tibetan-translator.py`，第 419–431 行（JavaScript 内嵌段）  
**优先级：** 中

**分析：** 当前 `doK()` 将用户输入的全部文本作为单一请求发送。Google Translate 非官方端点对单次请求存在未公开的字符数上限（实测约 5,000 字符），超出后可能返回截断结果或 HTTP 400 错误，且当前错误处理仅显示通用的「翻译失败」提示，用户无法得知问题原因。

藏文文献（如经典注疏、田野记录）往往较长，此问题在学术使用场景下尤为突出。

**建议方案：** 在 `doK()` 中按段落或字符数阈值自动分块：

```javascript
function splitText(text, maxLen = 4000) {
    // 优先按藏文句末标点（།）分割，其次按换行，最后按字符数截断
    const segments = [];
    const parts = text.split(/(?<=།)\s*/);  // 藏文句末标点
    let current = '';
    for (const part of parts) {
        if ((current + part).length > maxLen) {
            if (current) segments.push(current.trim());
            current = part;
        } else {
            current += part;
        }
    }
    if (current.trim()) segments.push(current.trim());
    return segments;
}
```

---

### I-4：`qt()` 去重仅检查队列中的待处理任务，不覆盖正在翻译的任务

**位置：** `tibetan-translator.py`，第 350–354 行（JavaScript 内嵌段）  
**优先级：** 低

**问题代码：**

```javascript
function qt(t, c = 'v') {
    if (tq.some(item => item.text === t && item.container === c)) return;  // 仅检查队列
    tq.push({ text: t, container: c });
    pq();
}
```

**分析：** 当某文本正在被 `pq()` 处理（即已从 `tq` 中 `shift()` 出来但 `await translate()` 尚未完成）时，相同文本可以绕过去重检查重新入队，导致同一句藏文被翻译两次并渲染两次字幕。在语音识别产生重复识别结果（常见于藏语识别）的场景下此问题尤为明显。

**建议修复：** 增加「正在翻译中」的文本集合：

```javascript
const tqInFlight = new Set();  // 当前正在翻译的文本键

function qt(t, c = 'v') {
    const key = `${c}:${t}`;
    if (tqInFlight.has(key)) return;
    if (tq.some(item => item.text === t && item.container === c)) return;
    tq.push({ text: t, container: c });
    pq();
}

async function pq() {
    if (ti) return;
    ti = true;
    const ver = qVersion;
    while (tq.length) {
        if (ver !== qVersion) { tq.length = 0; break; }
        const { text, container } = tq.shift();
        const key = `${container}:${text}`;
        tqInFlight.add(key);
        try {
            const r = await translate(text);
            if (ver !== qVersion) break;
            ad(container, text, r.text, r.src);
        } catch (e) {
            ts('翻译失败：' + (e.message || '网络异常'));
        } finally {
            tqInFlight.delete(key);
        }
    }
    ti = false;
    if (tq.length && ver === qVersion) pq();
}
```

---

### I-5：`install.sh` 文件完整性校验机制薄弱，存在供应链安全风险

**位置：** `install.sh`，第 76–87 行  
**优先级：** 中（安全层面）

**问题代码：**

```bash
if ! $PY -c "
with open('$INSTALL_DIR/$FILE', 'r') as f:
    content = f.read()
    assert 'ReusableTCPServer' in content, 'Missing ReusableTCPServer'
    assert 'find_port' in content, 'Missing find_port'
    assert 'def main' in content, 'Missing main'
" 2>/dev/null; then
    echo "  ⚠️  文件可能不完整，建议重新下载"
fi
```

**分析：** 该脚本通过 `curl | bash` 管道方式执行，是典型的高风险安装模式。当前的文件完整性校验仅检查三个字符串是否存在，无法防御：

1. **截断下载**：网络中断导致文件不完整，但仍可能包含这三个字符串。
2. **内容注入攻击**：中间人攻击（MITM）可在保留原有字符串的同时注入恶意代码。
3. **CDN 缓存投毒**：`raw.githubusercontent.com` 通过 Fastly CDN 分发，理论上存在缓存层攻击面。

**建议方案：**

在 README 和独立的 `checksums.txt` 中发布 SHA-256 哈希值，并在安装脚本中验证：

```bash
EXPECTED_SHA256="<在发布时填入的哈希值>"
ACTUAL_SHA256=$(sha256sum "$INSTALL_DIR/$FILE" | cut -d' ' -f1)
if [ "$ACTUAL_SHA256" != "$EXPECTED_SHA256" ]; then
    echo "  ❌ 文件校验失败，SHA-256 不匹配，请重新下载"
    rm -f "$INSTALL_DIR/$FILE"
    exit 1
fi
```

---

### I-6：`main()` 服务就绪等待逻辑硬编码 2 秒上限，无法适应高负载环境

**位置：** `tibetan-translator.py`，第 613–618 行（Python）  
**优先级：** 低

**问题代码：**

```python
for _ in range(20):     # 硬编码：最多 20 次 × 0.1s = 2 秒
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=0.1):
            break
    except OSError:
        time.sleep(0.1)
# ← 循环结束后无论是否成功，均继续执行 webbrowser.open
```

**分析：** 若系统负载较高（如 Docker 容器内、高并发场景），服务器可能在 2 秒内未能完成初始化，但程序仍会调用 `webbrowser.open()`，用户将看到浏览器显示连接被拒绝的错误页面。

**建议修复：**

```python
server_ready = False
for _ in range(20):
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=0.1):
            server_ready = True
            break
    except OSError:
        time.sleep(0.1)

if not server_ready:
    print(f"  ⚠️  服务器启动超时，请手动访问 {url}")
else:
    opened = False
    try:
        opened = webbrowser.open(url)
    except Exception:
        pass
    # ... 回退逻辑
```

---

### I-7：启动脚本 `start.command` 与 `启动翻译.bat` 缺乏 Python 版本检查

**位置：** `start.command`（全文）；`启动翻译.bat`（全文）  
**优先级：** 低

**问题代码：**

```bash
# start.command（macOS）
#!/bin/bash
cd "$(dirname "$0")"
python3 tibetan-translator.py   # ← 无版本检查
```

```bat
:: 启动翻译.bat（Windows）
@echo off
python tibetan-translator.py    :: ← 无版本检查，且未指定 python3
pause
```

**分析：** `install.sh` 已实现 Python 3.8+ 版本验证，但两个双击启动脚本均缺少此检查。macOS 系统自带 Python 2.7（Monterey 之前的版本），Windows 用户可能将 `python` 指向 Python 2.x，导致启动失败但错误信息难以理解。此外，bat 文件使用 `python` 而非 `python3`，在部分 Windows 环境中可能解析到错误版本。

---

### I-8：缺乏 HTTP 安全响应头

**位置：** `tibetan-translator.py`，`Handler` 类  
**优先级：** 低（本地服务，威胁面有限）

当前 HTTP 响应未包含以下安全头：

```
Content-Security-Policy: default-src 'self'; script-src 'unsafe-inline' cdn.jsdelivr.net translate.googleapis.com; ...
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
```

虽然服务仅绑定于 `127.0.0.1`，不对外网暴露，但若将来支持局域网模式（见 [F-5](#f-5-支持局域网共享模式)），这些响应头将变为必要的安全措施。

---

## 5. 功能扩展请求

### F-1：支持中文 → 藏语反向翻译

**优先级：** 高（核心使用场景扩展）

**分析：** 现有 Google Translate 调用仅硬编码 `sl=bo&tl=zh-CN`（藏→中），对藏语学习者和从事藏汉双语工作的研究人员而言，反向翻译（中→藏）具有同等重要的实用价值。实现成本极低：在 UI 中增加语言方向切换按钮，并动态调整 `sl`/`tl` 参数即可。

**UI 建议：** 在标题栏或翻译按钮旁添加「⇄」方向切换，并同步更新输入框占位文字（`placeholder`）和字体族（藏文字体 vs 汉文字体）。

---

### F-2：翻译历史的本地持久化与导出

**优先级：** 中（学术使用场景）

**现状：** README「已知限制」中明确列出「无历史持久化，刷新页面后记录清空」。然而，项目已内置 `localStorage` 基础设施用于翻译缓存，技术基础已具备。

**建议实现：** 将每条翻译记录（原文、译文、来源、时间戳、输入模式）存入 `localStorage`，并提供导出功能：

```javascript
function exportHistory(format = 'csv') {
    const records = JSON.parse(localStorage.getItem('tibetan_history') || '[]');
    if (format === 'csv') {
        const csv = ['时间,输入模式,藏文原文,中文译文,翻译来源',
            ...records.map(r => `"${r.time}","${r.mode}","${r.source}","${r.target}","${r.engine}"`)
        ].join('\n');
        downloadFile(csv, 'tibetan_translation_history.csv', 'text/csv');
    }
}
```

对于田野调查、语料库建设等学术场景，此功能价值显著。

---

### F-3：OCR 支持多页 PDF 文档

**优先级：** 中（学术文献使用场景）

**分析：** 藏文文献（贝叶经、长条书页扫描、学术出版物）绝大多数以多页 PDF 形式存在，当前 OCR 仅支持单张图片，严重限制了学术使用价值。

**技术方案：** 利用浏览器内置的 PDF 渲染能力（`pdf.js`）将每页渲染为 canvas，再逐页送入 Tesseract，全程在客户端完成，无需后端修改：

```javascript
import * as pdfjsLib from 'https://cdn.jsdelivr.net/npm/pdfjs-dist@4/build/pdf.min.mjs';

async function processPDF(file) {
    const arrayBuffer = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument(arrayBuffer).promise;
    const results = [];
    for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const canvas = await renderPageToCanvas(page, 300); // 300 DPI
        const { data: { text } } = await Tesseract.recognize(canvas, 'bod');
        results.push(text);
    }
    return results.join('\n\n');
}
```

---

### F-4：藏文软键盘（虚拟输入法辅助面板）

**优先级：** 中（用户体验，大幅降低使用门槛）

**分析：** 绝大多数用户设备未安装藏文输入法，键盘翻译模式对他们实际上不可用。藏文字母表（30 个辅音字母 + 4 个元音符号 + 常用叠字组合）数量有限，适合以软键盘形式呈现。

**建议实现：** 在键盘模式的 `textarea` 下方提供可折叠的藏文字符面板，支持 Unicode 直接插入：

```javascript
const TIBETAN_CONSONANTS = [
    'ཀ','ཁ','ག','ང','ཅ','ཆ','ཇ','ཉ',
    'ཏ','ཐ','ད','ན','པ','ཕ','བ','མ',
    'ཙ','ཚ','ཛ','ཝ','ཞ','ཟ','འ','ཡ',
    'ར','ལ','ཤ','ས','ཧ','ཨ'
];
const TIBETAN_VOWELS = ['ི','ུ','ེ','ོ'];
const TIBETAN_PUNCT = ['།','་','༎','༏'];
```

---

### F-5：支持局域网共享模式

**优先级：** 低（特定场景：田野调查、多人共用设备）

**分析：** 当前服务器硬绑定于 `127.0.0.1`，无法在局域网内共享。对于在藏区进行田野调查、多人使用同一翻译服务的场景，局域网模式具有实际价值。

**建议实现：** 支持命令行参数配置：

```python
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description='藏语→中文实时翻译工具')
    parser.add_argument('--host', default='127.0.0.1',
                        help='监听地址（默认 127.0.0.1，局域网共享请设为 0.0.0.0）')
    parser.add_argument('--port', type=int, default=9090,
                        help='监听端口（默认 9090）')
    return parser.parse_args()
```

启用局域网模式时，同步显示本机局域网 IP 地址及对应访问链接。

---

### F-6：引入持续集成（CI）与跨浏览器端到端测试

**优先级：** 中（工程质量）

**分析：** 现有 94 项单元测试全为 Python 静态分析，对以下运行时行为无覆盖：

- Web Speech API 在 Chrome/Edge 中的实际行为
- Tesseract.js CDN 加载与 OCR 准确率
- 跨标签页切换时翻译队列的并发行为
- `localStorage` 缓存的写入与恢复
- 移动端触控交互

**建议配置：** 在 GitHub Actions 中接入 Playwright：

```yaml
# .github/workflows/e2e.yml
jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install playwright && playwright install chromium
      - run: python tibetan-translator.py &
      - run: playwright test tests/e2e/
```

---

## 6. 测试体系评估

### 覆盖情况总结

| 测试模块 | 测试数 | 覆盖类型 | 盲区 |
|----------|--------|----------|------|
| `test_server.py` | 36 | Python HTTP 服务器行为 | 并发请求、异常路径 |
| `test_js_logic.py` | 30 | JS 函数签名、CSS 变量 | 运行时逻辑、异步流程 |
| `test_html.py` | 20 | HTML 结构完整性 | JS 逻辑差异、功能等价性 |
| `test_install.py` | 8 | Shell 脚本语法与内容 | 实际下载执行、网络行为 |

### 主要盲区

**测试盲区 1：`index.html` 与内嵌 HTML 仅比对 ID 数量**

`test_html.py` 的 `test_both_have_same_id_count` 仅确认两个文件中 `id="..."` 的数量相同，无法检测：
- JavaScript 函数体差异（如错误处理逻辑不一致）
- CSS 规则差异（如颜色变量值不同）
- HTML 结构差异（如某个 tab 面板内容不同）

**建议增加的测试：**

```python
def test_both_have_same_js_functions(self):
    """验证两个 HTML 文件包含相同的 JS 函数签名"""
    import re
    func_pattern = r'(?:async\s+)?function\s+(\w+)\s*\('
    embedded_funcs = set(re.findall(func_pattern, HTML))
    index_funcs = set(re.findall(func_pattern, INDEX_HTML))
    self.assertEqual(embedded_funcs, index_funcs,
                     f"JS function mismatch:\n"
                     f"  Only in embedded: {embedded_funcs - index_funcs}\n"
                     f"  Only in index.html: {index_funcs - embedded_funcs}")
```

**测试盲区 2：`qt()` 去重逻辑的覆盖缺失**

当前测试未验证重复入队场景，可以通过 Python 模拟 JavaScript Map 的行为进行静态验证。

**测试盲区 3：`pq()` 尾递归路径**

```javascript
if (tq.length && ver === qVersion) pq();  // 第 348 行：尾递归调用
```

在队列持续有新任务追加的场景下，此处存在理论上的调用栈积累风险（虽然受 `ti` 标志保护，但 `ti = false` 与尾递归 `pq()` 之间存在一个微小的时间窗口）。

---

## 7. 文档问题

### D-1：README「翻译缓存」章节描述与实际实现不符

**位置：** `README.md`，第 358–359 行

```markdown
- **存储位置：** 浏览器内存（Map 对象）
- **生命周期：** 页面刷新后清空
```

**实际实现：** 缓存通过 `localStorage` 持久化（`tibetan-translator.py` 第 194–218 行），页面刷新后会从 `localStorage` 恢复，生命周期不是「页面刷新后清空」，而是「直到用户手动清除浏览器数据」。该描述与代码实现完全相反，需修正。

---

### D-2：版本号内部不一致

| 位置 | 版本号 |
|------|--------|
| 启动横幅（`print`） | `v2.1` |
| HTML footer | `v2.1` |
| Python docstring（第 5 行） | `v2.1` |
| JS 注释（第 330 行） | `v2.2` |
| HTTP 服务器注释（第 529 行） | `v2.1` |
| README 更新日志 | `v2.1` |

第 330 行的 `// v2.2: 修复并发竞态` 与全部其他位置的 `v2.1` 不一致，可能是开发过程中的遗留注释，需统一或按实际情况更新版本号。

---

### D-3：README「已知限制」未列出 Google Translate 非官方端点风险

README「已知限制」章节列出了网络依赖、浏览器限制等问题，但未提及核心翻译引擎依赖非官方 API 端点这一重要限制，对依赖该工具进行稳定工作的用户存在误导。

---

## 8. 汇总矩阵

| 编号 | 类别 | 标题摘要 | 严重程度 | 优先级 |
|------|------|----------|----------|--------|
| B-1 | Bug | `clearTimeout` 在异常路径重复调用 | 低 | P4 |
| B-2 | Bug | `find_port` 端口耗尽时静默崩溃 | **高** | **P1** |
| B-3 | Bug | 语音错误码覆盖不完整 | 中 | P2 |
| B-4 | Bug | `ensureTesseract` 并发竞态 | 中 | P2 |
| B-5 | Bug | 双 HTML 版本漂移风险 | 中 | P2 |
| B-6 | Bug | `do_HEAD` 重复编码 + 版本号混乱 | 低 | P4 |
| B-7 | Bug | 空格键快捷键键盘导航冲突 | 低 | P4 |
| I-1 | 改进 | Google 私有端点架构风险 | **极高** | **P1** |
| I-2 | 改进 | 缓存 LRU 淘汰策略缺失 | 低 | P4 |
| I-3 | 改进 | 大文本缺乏分段处理 | 中 | P3 |
| I-4 | 改进 | `qt()` 去重未覆盖在途任务 | 低 | P3 |
| I-5 | 改进 | 安装脚本完整性校验薄弱 | 中（安全） | P2 |
| I-6 | 改进 | 服务就绪等待上限过短 | 低 | P4 |
| I-7 | 改进 | 启动脚本缺乏 Python 版本检查 | 低 | P4 |
| I-8 | 改进 | 缺乏 HTTP 安全响应头 | 低 | P4 |
| F-1 | 功能 | 中文→藏语反向翻译 | — | P2 |
| F-2 | 功能 | 翻译历史持久化与导出 | — | P3 |
| F-3 | 功能 | OCR 支持多页 PDF | — | P3 |
| F-4 | 功能 | 藏文软键盘 | — | P3 |
| F-5 | 功能 | 局域网共享模式 | — | P4 |
| F-6 | 功能 | CI + 端到端测试 | — | P2 |
| D-1 | 文档 | README 缓存描述与实现不符 | — | P3 |
| D-2 | 文档 | 内部版本号不一致 | — | P4 |
| D-3 | 文档 | 未披露 Google 非官方端点风险 | — | P3 |

---

## 9. 优先级路线图

### P1：立即处理（影响基本可用性）

1. **B-2**：修复 `find_port()` 端口耗尽时的崩溃问题，添加 `RuntimeError` 和用户指引。
2. **I-1**：规划 Google Translate 端点的备用方案，至少在 README 中明确披露该风险。

### P2：近期处理（影响核心功能稳定性）

3. **B-3**：完善语音识别错误码处理，覆盖所有 8 种 `SpeechRecognitionError` 类型。
4. **B-4**：用 Promise 单例锁修复 `ensureTesseract()` 竞态条件。
5. **B-5**：在 `test_html.py` 中增加 JS 函数签名一致性测试，或迁移至单一 HTML 来源。
6. **I-5**：在 `install.sh` 中引入 SHA-256 文件完整性校验。
7. **F-1**：实现中文→藏语反向翻译，成本极低但实用价值极高。
8. **F-6**：配置 GitHub Actions + Playwright 端到端测试。

### P3：中期迭代（功能增强）

9. **I-3**：键盘模式大文本自动分段翻译。
10. **I-4**：`qt()` 增加在途任务去重。
11. **F-2**：翻译历史本地持久化与 CSV 导出。
12. **F-3**：OCR 多页 PDF 支持。
13. **F-4**：藏文软键盘面板。
14. **D-1**：更正 README 中缓存生命周期的错误描述。
15. **D-3**：在「已知限制」中披露 Google 非官方端点风险。

### P4：低优先级（质量提升）

16. **B-1**：清理 `clearTimeout` 重复调用。
17. **B-6**：预计算 `_HTML_BYTES`，统一版本号。
18. **B-7**：改进空格键快捷键的焦点检测逻辑。
19. **I-2**：实现真正的 LRU 缓存淘汰。
20. **I-6**：服务就绪等待逻辑增加成功确认。
21. **I-7**：`start.command` 和 `启动翻译.bat` 增加 Python 版本检查。
22. **I-8**：添加基本 HTTP 安全响应头。
23. **F-5**：实现局域网共享模式（`--host 0.0.0.0`）。
24. **D-2**：统一内部版本号标注。

---

*报告由代码静态分析与手动审查生成，测试环境：Python 3.x，Ubuntu 24，94 项单元测试全部通过。*
