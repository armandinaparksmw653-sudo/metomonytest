FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive
ARG GF_URL=https://github.com/GrammaticalFramework/gf-core/releases/download/release-3.12/gf-3.12-ubuntu-24.04.deb
ARG GF_SHA256=17aa5452b713f1e00a0755a1bad998a926acbffb96eefde2c3800ca72536b4d8
ARG CUBICAL_COMMIT=132a2a3197b490c571356f0399a2a6fbfab40f2a
ARG RGL_COMMIT=e825d9223305ad3066e1ac5b276bcdedd2fcd15a

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       agda-bin \
       ca-certificates \
       cabal-install \
       curl \
       ghc \
       git \
       make \
       python3 \
       ripgrep \
       sudo \
    && rm -rf /var/lib/apt/lists/*

RUN curl --fail --location --retry 5 --retry-all-errors \
      "$GF_URL" \
      --output /tmp/gf.deb \
    && echo "$GF_SHA256  /tmp/gf.deb" | sha256sum --check --strict - \
    && apt-get update \
    && apt-get install -y --no-install-recommends /tmp/gf.deb \
    && rm -f /tmp/gf.deb \
    && rm -rf /var/lib/apt/lists/*

RUN git init /opt/cubical \
    && git -C /opt/cubical remote add origin https://github.com/agda/cubical.git \
    && git -C /opt/cubical fetch --depth 1 origin "$CUBICAL_COMMIT" \
    && git -C /opt/cubical checkout --detach FETCH_HEAD \
    && test "$(git -C /opt/cubical rev-parse HEAD)" = "$CUBICAL_COMMIT"

RUN git init /opt/gf-rgl \
    && git -C /opt/gf-rgl remote add origin https://github.com/GrammaticalFramework/gf-rgl.git \
    && git -C /opt/gf-rgl fetch --depth 1 origin "$RGL_COMMIT" \
    && git -C /opt/gf-rgl checkout --detach FETCH_HEAD \
    && test "$(git -C /opt/gf-rgl rev-parse HEAD)" = "$RGL_COMMIT" \
    && cd /opt/gf-rgl \
    && runghc Setup.hs build prelude lang api --langs=Eng --gf=gf \
    && runghc Setup.hs copy --dest=/opt/gf-rgl-lib

RUN if ! id -u ubuntu >/dev/null 2>&1; then \
      useradd --create-home --shell /bin/bash ubuntu; \
    fi \
    && printf 'ubuntu ALL=(ALL) NOPASSWD:ALL\n' >/etc/sudoers.d/ubuntu \
    && chmod 0440 /etc/sudoers.d/ubuntu \
    && chown -R ubuntu:ubuntu /opt/cubical /opt/gf-rgl /opt/gf-rgl-lib \
    && agda --version \
    && gf --version \
    && ghc --version \
    && python3 --version

ENV CUBICAL_LIB=/opt/cubical \
    RGL_LIB=/opt/gf-rgl-lib

USER ubuntu
WORKDIR /workspace
