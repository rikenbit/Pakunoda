FROM condaforge/mambaforge:latest

COPY envs/pakunoda.yaml /tmp/env.yaml
RUN mamba env create -f /tmp/env.yaml && mamba clean -afy

# Activate environment by default
ENV PATH=/opt/conda/envs/pakunoda/bin:$PATH

COPY . /app
WORKDIR /work

ENTRYPOINT ["snakemake"]
CMD ["--help"]
