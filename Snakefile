#
# Setting
#
envvars:
	"PAKUNODA_INDIR", # Input directory (e.g. test/data)
	"PAKUNODA_OUTDIR", # Output directory (e.g. test/results)
	"PAKUNODA_FOLDS", # No. of folds (e.g. 5)
	"PAKUNODA_INIT", # Initial value of factor matrices (?????)
	"PAKUNODA_THREADS", # No. of threads (e.g. 4)
	"PAKUNODA_GB" # Memory usage (e.g. 50)

INDIR = os.environ["PAKUNODA_INDIR"]
OUTDIR = os.environ["PAKUNODA_OUTDIR"]
FOLDS = os.environ["PAKUNODA_FOLDS"]
INIT = os.environ["PAKUNODA_INIT"]
THREADS = os.environ["PAKUNODA_THREADS"]
RESOURCE = os.environ["PAKUNODA_RESOURCE"]

DATASETs = glob_wildcards(INDIR + "/{dataset}.csv").dataset

rule all:
	input:
		expand(INDIR + "/{dataset}.csv",
			dataset=DATASETs)

# データの形が合っているか・同じ名前で統一されているか
rule datacheck:

# 行列化（3-order以上）
rule matricise:

# NMF, NTDなどで初期化
rule init:

# データを跨いだ時の対応するベクトルの並び順
rule sort:

# gcTensorパッケージでテンソル分解
rule gctensor:

# レポート
rule report:

# Data format conversion
rule csv2coo:
rule csv2csf:
rule csv2hicoo:

# results以下を全部削除
rule clearn:
