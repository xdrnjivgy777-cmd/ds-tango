"""
categorize_candidates.py — Bucket the 10000 candidates into 7 DS categories
using a keyword-based heuristic. Helps the curator pick the final 300.

Output: scripts/extraction/by_category/{category}.csv
Also prints top-N per category to stdout for review.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

CSV_IN = Path("/Users/shanlei/Desktop/ds-tango/scripts/extraction/candidates.csv")
OUT_DIR = Path("/Users/shanlei/Desktop/ds-tango/scripts/extraction/by_category")

# Hard rejection list — high-frequency words that are NOT DS terms
# but template/admin/operational vocabulary from course materials.
HARD_REJECT = {
    "授業シート", "講師", "講師名", "参照資料", "授業コメント", "配布テキスト",
    "クラス教科名", "科目名", "科⽬名", "教科名", "教科", "科目", "教材",
    "成績評価", "履修判定試験", "シラバス内容", "コマシラバス", "シラバス",
    "学習内容", "授業", "資料", "配布", "配布資料", "提出", "成績", "資格",
    "資格関連度", "学校", "学園", "校内", "校外", "学⽣", "学生", "受講",
    "受講者", "受講生", "出席", "欠席", "遅刻", "卒業", "入学",
    "学籍番号", "氏名", "選択科目", "履修", "今日", "今⽇", "本⽇", "本日",
    "前回", "次回", "今回", "毎回", "全回", "各回",
    "試験", "テスト", "検定", "問題集", "解答", "解説", "回答",
    "ポイント", "キーポイント", "重要ポイント",
    "確認", "説明", "理解", "把握", "判断",
    "目的", "目標", "科目目標", "学習目的", "学習目標",
    "授業時間", "授業日", "実施日", "提出日", "実施", "予定", "計画",
    "グループワーク", "個人作業", "宿題", "作業",
    "電源", "起動", "終了", "ログイン", "ログアウト",
    "資料配布", "提出物",
    "応募", "募集", "採用", "就職", "転職", "進路",
    "備考", "概要", "目次", "本書", "本章", "本節", "前章", "次章",
    "ガイダンス", "案内", "問合せ", "お問い合わせ",
    "本人", "他人", "自分", "代表", "代表者",
    "全体", "全部", "全て", "個別", "個々",
    "通り", "代わり", "違い", "多く", "以下", "以上", "以外", "程度", "概念",
    "意見", "知識", "意味", "全体像", "現在", "従来", "新規", "既存",
    "範囲", "形式", "形態", "性質",
    "開発", "改善", "解決", "対応", "対象", "効率", "効果", "影響",
    "予定", "予想", "報告", "紹介", "紹介資料",
    "主体", "客体", "受益者", "提供者",
    # Generic verbs/actions that aren't DS terms
    "実行", "実施", "実装", "適用", "活用", "利用", "使用", "使い方",
    "操作", "選択", "指定", "検索", "整理", "管理", "保存", "削除", "追加",
    "変更", "移動", "終了", "開始", "発生", "存在", "提示",
    "表示", "出力", "入力", "表現", "記述", "記録", "格納",
    "集計", "計算", "算出", "判定", "推定", "予測",  # ← reconsider: 推定/予測 are core DS, keep
    "正解", "誤り", "正常", "異常",
    "条件", "基本", "基礎", "基準", "標準", "通常", "一般",
    "場面", "状況", "状態", "様子", "段階", "順序", "手順", "流れ", "仕組み", "方式",
    "方法", "手法",  # ← borderline — 手法 is technical-ish but very generic
    "種類", "分類", "分野", "領域", "ジャンル",  # ← 分類 is core DS, restore later
    "成果", "結果", "経緯", "原因", "理由",
    "場合", "事例", "ケース", "例", "例題",
    "情報", "内容", "本文",  # ← 情報 borderline — used in 情報セキュリティ etc but mostly daily
    "技術", "知見", "経験",  # 技術 borderline
    "学習", "勉強", "練習", "演習", "実習", "実践",  # ← 学習 is part of 機械学習 but as a standalone everyday
    "文字", "数字", "記号",  # ← 文字 not a DS term
    "用途", "用語", "用例",
    "自動", "手動", "半自動",
    "機能", "性能", "機能性",
    "全般", "全面", "両方", "片方", "両側",
    # Course names themselves
    "情報リテラシー", "PCリテラシー", "コンピュータシステム", "アルゴリズム",
    # Misc filler
    "問題", "課題", "事項", "項目", "事項",
    "代表的", "全体的", "基本的",
    # 数字混在
    "点満点", "回答数", "問題数",
}

# Restore words we mistakenly hard-rejected (these ARE core DS terms)
RESTORE = {
    "推定", "予測", "分類", "学習", "確率", "標準", "標準偏差",
    "情報", "技術",  # keep these for compounds; the bare word may be borderline
}
HARD_REJECT -= RESTORE

# Category keyword markers (substring match)
CATEGORIES = {
    "統計学": [
        "統計", "確率", "分布", "平均", "中央値", "中央", "分散", "標準偏差", "偏差",
        "相関", "回帰", "推定", "推論", "検定", "仮説", "信頼区間", "区間",
        "標本", "母集団", "母平均", "母分散", "サンプリング", "サンプル",
        "正規", "二項", "ポアソン", "指数分布", "ベルヌーイ",
        "尤度", "事後", "事前", "ベイズ",
        "p値", "有意", "自由度", "誤差", "残差",
        "期待値", "分位", "四分位", "歪度", "尖度",
        "離散", "連続", "確率変数", "確率密度",
        "ヒストグラム", "箱ひげ", "散布図",
        "最尤", "最小二乗",
    ],
    "機械学習": [
        "機械学習", "深層学習", "ディープラーニング", "ニューラル",
        "教師", "教師あり", "教師なし", "強化学習", "半教師",
        "回帰", "分類", "クラスタリング", "クラスター", "クラスタ",
        "決定木", "ランダムフォレスト", "サポートベクター",
        "k-means", "kmeans", "kNN",
        "特徴", "特徴量", "特徴抽出", "ラベル", "予測", "推論",
        "モデル", "アルゴリズム", "学習率", "学習係数",
        "過学習", "過剰適合", "過適合", "汎化", "正則化", "正規化",
        "勾配", "降下", "最適化", "損失", "誤差", "コスト",
        "活性化", "シグモイド", "ソフトマックス", "リル", "ReLU",
        "パーセプトロン", "畳み込み", "プーリング",
        "バッチ", "エポック", "イテレーション",
        "訓練", "検証", "テストデータ", "訓練データ",
        "交差検証", "クロスバリデーション", "ホールドアウト",
        "精度", "再現率", "適合率", "F値", "AUC", "ROC", "混同行列",
        "正解率", "誤識別", "誤分類",
        "ハイパーパラメータ", "パラメータ",
        "アンサンブル", "バギング", "ブースティング",
        "次元削減", "主成分", "PCA", "次元",
        "異常検知", "外れ値",
        "強化学習", "報酬", "方策", "Q学習",
        "GAN", "Transformer", "BERT", "GPT", "RNN", "LSTM", "CNN",
    ],
    "データベース": [
        "データベース", "DB", "テーブル", "レコード", "フィールド", "カラム",
        "SQL", "クエリ", "クエリー", "結合", "JOIN", "インナー", "アウター",
        "正規化", "第一正規形", "第二正規形", "第三正規形",
        "主キー", "外部キー", "一意", "ユニーク", "インデックス", "索引",
        "トランザクション", "コミット", "ロールバック",
        "ビュー", "ストアドプロシージャ", "トリガー",
        "リレーショナル", "リレーション",
        "ERD", "ER図", "エンティティ", "属性", "実体",
        "DML", "DDL", "DCL",
        "CRUD", "INSERT", "UPDATE", "DELETE", "SELECT",
        "集約", "GROUP BY", "ORDER BY", "WHERE",
        "NoSQL", "MongoDB",
    ],
    "Python": [
        "変数", "関数", "引数", "戻り値", "返り値",
        "型", "整数", "浮動小数", "文字列", "ブール", "リスト", "タプル", "辞書", "セット",
        "配列", "オブジェクト", "クラス", "インスタンス", "継承", "メソッド", "属性",
        "ライブラリ", "モジュール", "パッケージ", "import",
        "ループ", "繰り返し", "イテレーション", "for文", "while文", "if文",
        "条件分岐", "条件式",
        "例外", "try", "except", "エラー", "デバッグ",
        "関数定義", "ラムダ式", "ラムダ", "無名関数",
        "リスト内包", "ジェネレータ",
        "pandas", "numpy", "matplotlib", "seaborn", "scikit-learn", "sklearn",
        "Jupyter", "ノートブック", "Colab",
        "DataFrame", "Series", "ndarray",
        "コード", "スクリプト", "プログラム", "コメント",
        "コーディング", "プログラミング",
    ],
    "可視化": [
        "可視化", "可視", "グラフ", "プロット", "チャート", "図",
        "ヒストグラム", "棒グラフ", "折れ線", "散布図", "円グラフ", "箱ひげ",
        "ヒートマップ", "等高線", "バブル", "レーダー",
        "軸", "凡例", "ラベル", "目盛", "タイトル",
        "色", "配色", "カラーマップ",
        "ダッシュボード", "可視化ツール", "Tableau",
        "matplotlib", "seaborn", "Plotly",
    ],
    "前処理": [
        "前処理", "クレンジング", "データクレンジング",
        "欠損", "欠損値", "欠測", "補完", "穴埋め",
        "外れ値", "異常値", "ノイズ",
        "正規化", "標準化", "スケーリング", "min-max",
        "エンコーディング", "ワンホット", "ラベルエンコード",
        "ダミー変数", "カテゴリ変数",
        "サンプリング", "リサンプリング", "アップサンプリング", "ダウンサンプリング",
        "結合", "マージ", "連結", "concat",
        "集約", "ピボット", "ピボットテーブル",
        "変換", "型変換", "キャスト",
        "重複", "重複削除",
        "集計", "groupby", "グループ化",
        "ソート", "並び替え", "並べ替え",
        "フィルタ", "フィルタリング", "抽出",
        "整形", "形式変換",
    ],
    "業務": [
        "意思決定", "ビジネス", "KPI", "ROI",
        "PoC", "プロトタイプ",
        "要件", "要件定義", "ドキュメント", "仕様",
        "プロジェクト", "マネジメント", "進捗",
        "セキュリティ", "個人情報", "プライバシー", "認証", "暗号", "暗号化",
        "クラウド", "AWS", "Azure", "GCP", "サーバ", "サーバー",
        "API", "REST", "JSON", "XML", "HTTP",
        "ETL", "データパイプライン", "パイプライン",
        "データウェアハウス", "データマート",
        "ビッグデータ", "データレイク",
        "AI", "人工知能",
    ],
}


def categorize(word: str) -> list[str]:
    """Assign zero or more categories to a word based on substring match."""
    cats = []
    for cat, kws in CATEGORIES.items():
        for kw in kws:
            if kw == word or kw in word:
                cats.append(cat)
                break
    return cats


def main():
    rows = list(csv.DictReader(CSV_IN.open(encoding="utf-8")))
    print(f"Loaded {len(rows)} candidates.\n")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    by_cat: dict[str, list[dict]] = defaultdict(list)
    uncategorized = []
    for r in rows:
        word = r["word"]
        if word in HARD_REJECT:
            continue
        cats = categorize(word)
        if not cats:
            uncategorized.append(r)
            continue
        # Assign to the first (primary) category only for the per-category file
        primary = cats[0]
        r2 = dict(r)
        r2["categories"] = "|".join(cats)
        by_cat[primary].append(r2)

    # Write per-category CSVs
    for cat, items in by_cat.items():
        out_path = OUT_DIR / f"{cat}.csv"
        with out_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=[
                "word", "reading", "freq_total", "course_count",
                "categories", "top_courses", "sample_sentence", "score"
            ])
            w.writeheader()
            for it in items:
                w.writerow(it)
        print(f"  {cat}: {len(items)} terms -> {out_path}")

    # Uncategorized — top by score, may have missed DS terms
    uncategorized.sort(key=lambda r: -int(r["score"]))
    unc_path = OUT_DIR / "_uncategorized.csv"
    with unc_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "word", "reading", "freq_total", "course_count",
            "top_courses", "sample_sentence", "score"
        ])
        w.writeheader()
        for it in uncategorized[:500]:
            w.writerow(it)
    print(f"  uncategorized (top 500): {len(uncategorized)} -> {unc_path}")

    # Print top 25 per category to stdout
    for cat, items in by_cat.items():
        print(f"\n=== {cat} (top 25 of {len(items)}) ===")
        for r in items[:25]:
            print(f"  {r['word']:<16} freq={r['freq_total']:>5} courses={r['course_count']:>3}")


if __name__ == "__main__":
    main()
