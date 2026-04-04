FROM condaforge/mambaforge:latest

COPY envs/pakunoda.yaml /tmp/env.yaml
RUN mamba env create -f /tmp/env.yaml && mamba clean -afy

ENV PATH=/opt/conda/envs/pakunoda/bin:$PATH

# Install remaining R packages from CRAN that are not on conda.
# mixOmics is installed via conda (bioconductor-mixomics).
# Core mwTensor deps (rTensor, nnTensor, ccTensor, iTensor) are on CRAN.
# mwTensor itself is only on GitHub.
RUN Rscript -e '\
  install.packages( \
    c("rTensor", "nnTensor", "ccTensor", "iTensor"), \
    repos = "https://cloud.r-project.org", quiet = TRUE); \
  remotes::install_github("rikenbit/mwTensor", upgrade = "never", quiet = TRUE)'

COPY . /app
WORKDIR /work

ENTRYPOINT ["snakemake"]
CMD ["--help"]
