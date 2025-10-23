import os
import argparse
from datetime import datetime

class DirectoryScanner:
    """
    ファイル構成をスキャンしてツリー形式で表示するクラス。
    """

    def __init__(self, root_path, max_depth=-1, ignore_dirs=None, show_details=False):
        """
        コンストラクタ

        :param root_path: スキャンを開始するルートパス
        :param max_depth: スキャンする最大の深さ (-1は無制限)
        :param ignore_dirs: 無視するディレクトリ名のセット
        :param show_details: ファイルサイズや更新日時などの詳細を表示するかどうか
        """
        self.root_path = os.path.abspath(root_path)
        self.max_depth = max_depth
        self.ignore_dirs = ignore_dirs if ignore_dirs else set()
        self.show_details = show_details
        
        # 統計情報
        self.file_count = 0
        self.dir_count = 0
        self.total_size = 0
        
        # 出力結果を保持するリスト
        self.tree_lines = []

    def _format_size(self, size_bytes):
        """バイト数を人間が読みやすい形式（KB, MB, GB）に変換する"""
        if size_bytes == 0:
            return "0B"
        size_name = ("B", "KB", "MB", "GB", "TB")
        i = 0
        while size_bytes >= 1024 and i < len(size_name) - 1:
            size_bytes /= 1024.0
            i += 1
        return f"{size_bytes:.2f}{size_name[i]}"

    def _scan_recursive(self, current_path, prefix="", level=0):
        """
        再帰的にディレクトリをスキャンする内部メソッド
        """
        # 最大深度に達したらそれ以上は潜らない
        if self.max_depth != -1 and level >= self.max_depth:
            return

        try:
            # 無視リストとドットファイルを除いたアイテムリストを取得
            items = sorted([item for item in os.listdir(current_path) if not item.startswith('.')])
        except PermissionError:
            self.tree_lines.append(f"{prefix}└── [アクセスが拒否されました]")
            return
        
        # 後で使うためにディレクトリを先に処理
        dirs = [item for item in items if os.path.isdir(os.path.join(current_path, item)) and item not in self.ignore_dirs]
        files = [item for item in items if os.path.isfile(os.path.join(current_path, item))]
        
        # ディレクトリとファイルを結合
        entries = dirs + files
        
        for i, item in enumerate(entries):
            path = os.path.join(current_path, item)
            is_last = (i == len(entries) - 1)
            
            # ツリーの接続詞を設定
            connector = "└── " if is_last else "├── "
            line = f"{prefix}{connector}{item}"

            if os.path.isdir(path):
                self.dir_count += 1
                self.tree_lines.append(line)
                # 次の階層のプレフィックスを計算
                next_prefix = prefix + ("    " if is_last else "│   ")
                self._scan_recursive(path, next_prefix, level + 1)
            else: # ファイルの場合
                self.file_count += 1
                try:
                    stats = os.stat(path)
                    size = stats.st_size
                    self.total_size += size
                    if self.show_details:
                        mtime = datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M')
                        line += f"  ({self._format_size(size)}, {mtime})"
                    else:
                         line += f"  ({self._format_size(size)})"
                except OSError:
                    line += "  [読み取りエラー]"
                self.tree_lines.append(line)

    def scan(self):
        """
        スキャンを実行し、結果を文字列として返す
        """
        self.tree_lines.append(f"{os.path.basename(self.root_path)}/")
        self.dir_count += 1 # ルートディレクトリをカウント
        self._scan_recursive(self.root_path)

        # サマリー（概要）を追加
        summary = [
            "\n" + "="*40,
            "スキャン概要",
            "="*40,
            f"合計ディレクトリ数: {self.dir_count}",
            f"合計ファイル数:     {self.file_count}",
            f"合計サイズ:         {self._format_size(self.total_size)}",
            "="*40,
        ]
        self.tree_lines.extend(summary)
        return "\n".join(self.tree_lines)

def main():
    """
    コマンドライン引数を処理し、スキャナを実行するメイン関数
    """
    parser = argparse.ArgumentParser(description="指定されたディレクトリのファイル構成をスキャンし、ツリー形式で表示します。")
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="スキャンするディレクトリのパス (デフォルト: カレントディレクトリ)"
    )
    parser.add_argument(
        "-d", "--depth",
        type=int,
        default=-1,
        help="スキャンする最大の深さ (デフォルト: 無制限)"
    )
    parser.add_argument(
        "-i", "--ignore",
        nargs="+",
        default=[".git", "__pycache__", ".vscode", "node_modules"],
        help="無視するディレクトリ名のリスト (デフォルト: .git __pycache__ .vscode node_modules)"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="結果を出力するファイル名"
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="ファイルサイズに加えて最終更新日時も表示する"
    )

    args = parser.parse_args()

    if not os.path.isdir(args.path):
        print(f"エラー: 指定されたパス '{args.path}' はディレクトリではありません。")
        return

    # スキャナを初期化
    scanner = DirectoryScanner(
        root_path=args.path,
        max_depth=args.depth,
        ignore_dirs=set(args.ignore),
        show_details=args.details
    )
    
    # スキャンを実行して結果を取得
    result = scanner.scan()
    
    # 結果を表示
    print(result)
    
    # ファイルに出力
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(result)
            print(f"\n結果を '{args.output}' に保存しました。")
        except IOError as e:
            print(f"エラー: ファイル '{args.output}' に書き込めませんでした: {e}")

if __name__ == "__main__":
    main()