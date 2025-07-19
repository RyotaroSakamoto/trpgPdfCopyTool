import streamlit as st
import pypdf
import re
from streamlit.components.v1 import html

st.set_page_config(page_title="PDF Text Extractor", layout="wide")

# CSSスタイルの設定（余白やボタンのデザイン調整）
st.markdown("""
<style>
    .stExpander {
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
    }
    .streamlit-expanderContent {
        margin-top: 0px !important;
        padding-top: 0px !important;
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    div[data-testid="stVerticalBlock"] {
        gap: 0.5rem !important;
    }
    .stTextArea {
        margin-bottom: 0px !important;
    }
    /* テキストエリアとボタンを横並びにするスタイル */
    .text-with-button {
        display: flex;
        align-items: flex-start;
        margin-bottom: 5px;
        width: 100%;
    }
    .copy-button {
        padding: 5px 10px;
        background-color: #4CAF50;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        height: fit-content;
        margin-right: 10px;
        min-width: 80px;
        flex-shrink: 0;
        transition: background-color 0.3s;
    }
    .copy-button:hover {
        background-color: #45a049;
    }
    .remove-newline-button {
        padding: 5px 10px;
        background-color: #2196F3;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        height: fit-content;
        margin-right: 10px;
        min-width: 100px;
        flex-shrink: 0;
        transition: background-color 0.3s;
    }
    .remove-newline-button:hover {
        background-color: #0b7dda;
    }
    .restore-button {
        padding: 5px 10px;
        background-color: #FF9800;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        height: fit-content;
        margin-right: 10px;
        min-width: 100px;
        flex-shrink: 0;
        transition: background-color 0.3s;
    }
    .restore-button:hover {
        background-color: #e68900;
    }
    .text-area-container {
        flex-grow: 1;
        width: calc(100% - 200px);
    }
    .text-area-container textarea {
        width: 100%;
        resize: vertical;
        min-width: 500px;
    }
    .split-options {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 20px;
        border: 1px solid #ddd;
    }
</style>
""", unsafe_allow_html=True)

st.title("PDFテキスト抽出 & コピー可能なブロック表示")
st.write("PDFファイルをアップロードして、テキストを適切に分割してブロック表示します。各ブロックは選択してコピーできます。")

uploaded_file = st.file_uploader("PDFファイルをアップロード", type="pdf")

def extract_text_from_pdf(file):
    pdf_reader = pypdf.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text

def smart_split_text(text, split_method="auto"):
    """
    テキストを適切な方法で分割する
    """
    if split_method == "blank_lines":
        # 従来の空白行分割
        blocks = re.split(r'\n\s*\n+', text)
        blocks = [block.strip() for block in blocks if block.strip()]
        
    elif split_method == "sentences":
        # 文単位で分割（句点、疑問符、感嘆符で分割）
        sentences = re.split(r'[。！？]', text)
        blocks = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                # 句点を復活
                if not sentence.endswith(('。', '！', '？')):
                    sentence += '。'
                blocks.append(sentence)
                
    elif split_method == "paragraphs":
        # 段落分割（改行で分割し、短すぎる行は前の行に結合）
        lines = text.split('\n')
        blocks = []
        current_block = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_block:
                    blocks.append(current_block.strip())
                    current_block = ""
                continue
                
            # 短い行（30文字未満）は前の行と結合
            if len(line) < 30 and current_block:
                current_block += " " + line
            else:
                if current_block:
                    blocks.append(current_block.strip())
                current_block = line
                
        if current_block:
            blocks.append(current_block.strip())
            
    elif split_method == "length":
        # 文字数で分割（約200文字ごと）
        block_size = 200
        blocks = []
        current_pos = 0
        
        while current_pos < len(text):
            end_pos = min(current_pos + block_size, len(text))
            
            # 文の途中で切れないよう調整
            if end_pos < len(text):
                # 次の句読点まで延長
                while end_pos < len(text) and text[end_pos] not in '。！？\n':
                    end_pos += 1
                if end_pos < len(text):
                    end_pos += 1
                    
            block = text[current_pos:end_pos].strip()
            if block:
                blocks.append(block)
            current_pos = end_pos
            
    else:  # auto
        # 自動判定：空白行が多い場合は空白行分割、少ない場合は段落分割
        blank_lines = len(re.findall(r'\n\s*\n+', text))
        total_lines = len(text.split('\n'))
        
        if blank_lines > total_lines * 0.1:  # 空白行が10%以上
            blocks = smart_split_text(text, "blank_lines")
        else:
            blocks = smart_split_text(text, "paragraphs")
    
    return [block for block in blocks if block.strip()]

def remove_newlines(text):
    """
    改行を削除し、すべての空白文字も削除する関数
    """
    # 改行を削除
    text = re.sub(r'\r?\n', '', text)
    # すべての空白文字（スペース、タブなど）を削除
    text = re.sub(r'\s', '', text)
    return text

# クリップボードコピー用のHTMLコンポーネント（個別ブロック用）
def text_with_copy_button(text, key):
    import html as html_module
    import json
    
    # JSONエンコードで安全にエスケープ
    text_json = json.dumps(text)
    text_without_newlines_json = json.dumps(remove_newlines(text))
    
    newline_count = text.count('\n')
    # 改行数に応じた高さを計算（最小値を設定）
    height = max(80, 30 + 20 * newline_count)
    
    # HTMLエスケープでテキストエリアの内容を安全に表示
    text_html_escaped = html_module.escape(text)
    
    component_html = f"""
    <div class="text-with-button">
        <button class="copy-button" id="copy-btn-{key}">コピー</button>
        <button class="remove-newline-button" id="newline-btn-{key}">改行削除</button>
        <div class="text-area-container">
            <textarea id="text_{key}" style="height: {height}px; padding: 8px; width: 100%;">{text_html_escaped}</textarea>
        </div>
    </div>
    <script>
    (function() {{
        const copyBtn = document.getElementById('copy-btn-{key}');
        const newlineBtn = document.getElementById('newline-btn-{key}');
        const textarea = document.getElementById('text_{key}');
        
        let isNewlineRemoved = false;
        const originalText = {text_json};
        const textWithoutNewlines = {text_without_newlines_json};
        
        // ボタンが既に処理済みかチェック
        if (copyBtn && newlineBtn && !copyBtn.hasAttribute('data-processed')) {{
            copyBtn.setAttribute('data-processed', 'true');
            newlineBtn.setAttribute('data-processed', 'true');
            
            // コピーボタンの処理
            copyBtn.addEventListener('click', function(e) {{
                e.preventDefault();
                if (textarea) {{
                    navigator.clipboard.writeText(textarea.value).then(function() {{
                        const originalBtnText = copyBtn.textContent;
                        copyBtn.textContent = 'コピー完了!';
                        copyBtn.style.backgroundColor = '#45a049';
                        setTimeout(function() {{
                            copyBtn.textContent = originalBtnText;
                            copyBtn.style.backgroundColor = '#4CAF50';
                        }}, 2000);
                    }}).catch(function(err) {{
                        console.error('コピーに失敗しました:', err);
                    }});
                }}
            }});
            
            // 改行削除/元に戻すボタンの処理
            newlineBtn.addEventListener('click', function(e) {{
                e.preventDefault();
                if (textarea) {{
                    if (!isNewlineRemoved) {{
                        // 改行を削除
                        textarea.value = textWithoutNewlines;
                        newlineBtn.textContent = '元に戻す';
                        newlineBtn.className = 'restore-button';
                        isNewlineRemoved = true;
                        
                        // クリップボードにコピー
                        navigator.clipboard.writeText(textWithoutNewlines).catch(function(err) {{
                            console.error('コピーに失敗しました:', err);
                        }});
                    }} else {{
                        // 元に戻す
                        textarea.value = originalText;
                        newlineBtn.textContent = '改行削除';
                        newlineBtn.className = 'remove-newline-button';
                        isNewlineRemoved = false;
                    }}
                }}
            }});
        }}
    }})();
    </script>
    """
    
    return html(component_html, height=(height + 40))

# 全テキストのコピー用のHTMLコンポーネント
def all_text_with_copy_button(text, key="all_text"):
    import html as html_module
    import json
    
    # JSONエンコードで安全にエスケープ
    text_json = json.dumps(text)
    text_without_newlines_json = json.dumps(remove_newlines(text))
    
    # HTMLエスケープでテキストエリアの内容を安全に表示
    text_html_escaped = html_module.escape(text)
    
    component_html = f"""
    <div class="text-with-button">
        <button class="copy-button" id="copy-btn-{key}">すべてコピー</button>
        <button class="remove-newline-button" id="newline-btn-{key}">改行削除</button>
        <div class="text-area-container">
            <textarea id="text_{key}" style="height: 100px; padding: 8px; width: 100%;">{text_html_escaped}</textarea>
        </div>
    </div>
    <script>
    (function() {{
        const copyBtn = document.getElementById('copy-btn-{key}');
        const newlineBtn = document.getElementById('newline-btn-{key}');
        const textarea = document.getElementById('text_{key}');
        
        let isNewlineRemoved = false;
        const originalText = {text_json};
        const textWithoutNewlines = {text_without_newlines_json};
        
        // ボタンが既に処理済みかチェック
        if (copyBtn && newlineBtn && !copyBtn.hasAttribute('data-processed')) {{
            copyBtn.setAttribute('data-processed', 'true');
            newlineBtn.setAttribute('data-processed', 'true');
            
            // コピーボタンの処理
            copyBtn.addEventListener('click', function(e) {{
                e.preventDefault();
                if (textarea) {{
                    navigator.clipboard.writeText(textarea.value).then(function() {{
                        copyBtn.textContent = 'コピー完了!';
                        copyBtn.style.backgroundColor = '#45a049';
                        setTimeout(function() {{
                            copyBtn.textContent = 'すべてコピー';
                            copyBtn.style.backgroundColor = '#4CAF50';
                        }}, 2000);
                    }}).catch(function(err) {{
                        console.error('コピーに失敗しました:', err);
                    }});
                }}
            }});
            
            // 改行削除/元に戻すボタンの処理
            newlineBtn.addEventListener('click', function(e) {{
                e.preventDefault();
                if (textarea) {{
                    if (!isNewlineRemoved) {{
                        // 改行を削除
                        textarea.value = textWithoutNewlines;
                        newlineBtn.textContent = '元に戻す';
                        newlineBtn.className = 'restore-button';
                        isNewlineRemoved = true;
                        
                        // クリップボードにコピー
                        navigator.clipboard.writeText(textWithoutNewlines).catch(function(err) {{
                            console.error('コピーに失敗しました:', err);
                        }});
                    }} else {{
                        // 元に戻す
                        textarea.value = originalText;
                        newlineBtn.textContent = '改行削除';
                        newlineBtn.className = 'remove-newline-button';
                        isNewlineRemoved = false;
                    }}
                }}
            }});
        }}
    }})();
    </script>
    """
    
    return html(component_html, height=170)

if uploaded_file is not None:
    try:
        # PDFからテキストを抽出
        text = extract_text_from_pdf(uploaded_file)
        
        # 分割方法選択UI
        st.markdown('<div class="split-options">', unsafe_allow_html=True)
        st.subheader("📝 テキスト分割方法を選択")
        
        col1, col2 = st.columns(2)
        
        with col1:
            split_method = st.selectbox(
                "分割方法",
                options=["auto", "blank_lines", "paragraphs", "sentences", "length"],
                format_func=lambda x: {
                    "auto": "🤖 自動判定（推奨）",
                    "blank_lines": "📄 空白行で分割",
                    "paragraphs": "📝 段落で分割", 
                    "sentences": "📖 文単位で分割",
                    "length": "📏 文字数で分割"
                }[x],
                index=0
            )
        
        with col2:
            st.info({
                "auto": "空白行の量を判定して最適な方法を自動選択",
                "blank_lines": "空白行（改行のみの行）でテキストを分割",
                "paragraphs": "改行と文の長さを考慮して段落ごとに分割",
                "sentences": "句点（。！？）で文単位に分割",
                "length": "約200文字ごとに分割（文の途中では切らない）"
            }[split_method])
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # テキストブロックに分割
        blocks = smart_split_text(text, split_method)
        
        # サイドバーにオプションを表示
        with st.sidebar:
            st.header("📋 オプション")
            
            # すべてのテキストをコピーするボタン
            st.write("### すべてのテキスト")
            all_text_with_copy_button(text)
            
            # 統計情報
            st.write("### 📊 統計情報")
            st.metric("抽出ブロック数", len(blocks))
            st.metric("総文字数", len(text))
            st.metric("総行数", len(text.split('\n')))
        
        # メイン画面にブロックを表示
        st.header(f"📝 抽出されたテキストブロック ({len(blocks)}個)")
        
        if len(blocks) == 0:
            st.warning("⚠️ テキストブロックが見つかりませんでした。別の分割方法を試してください。")
        else:
            for i, block in enumerate(blocks):
                with st.expander(f"ブロック {i+1} ({len(block)}文字)", expanded=True):
                    text_with_copy_button(block, f"block_{i}")
    
    except Exception as e:
        st.error(f"❌ エラーが発生しました: {str(e)}")
else:
    st.info("📄 PDFファイルをアップロードしてください。")

# アプリの使い方ガイド
with st.expander("📖 使い方ガイド"):
    st.markdown("""
    ### 🚀 使い方ガイド
    
    **1. PDFアップロード**
    - 左上の「PDFファイルをアップロード」ボタンからPDFファイルを選択
    
    **2. 分割方法の選択**
    - **🤖 自動判定（推奨）**: PDFの構造を分析して最適な方法を自動選択
    - **📄 空白行で分割**: 空白行がある文書に適している
    - **📝 段落で分割**: 一般的な文書に適している  
    - **📖 文単位で分割**: 細かく分割したい場合
    - **📏 文字数で分割**: 一定の長さで分割したい場合
    
    **3. テキストのコピー**
    - 各ブロックの「コピー」ボタン：そのブロックをクリップボードにコピー
    - 「改行削除」ボタン：改行と空白をすべて削除してコピー
    - 「元に戻す」ボタン：元のテキストに戻す
    
    **4. 便利機能**
    - サイドバーで全体統計を確認
    - 「すべてのテキスト」で文書全体をコピー
    - ブロックは折りたたみ表示で見やすく整理
    
    ### ⚠️ 注意点
    - PDFの構造によってはテキスト抽出の精度が変わる場合があります
    - 画像主体のPDFでは正確に抽出できないことがあります
    - 分割がうまくいかない場合は別の分割方法を試してください
    """)
