FROM minidocks/texlive:2023-medium

RUN tlmgr install \
      latexmk \
      preprint \
      titlesec \
      marvosym \
      enumitem \
      fancyhdr \
      babel-english \
      hyphen-english \
      xifthen \
      ifmtarg \
      etoolbox \
      setspace \
      fontspec \
      unicode-math \
      fontawesome \
      sourcesanspro \
      tcolorbox \
      environ \
      parskip \
      ragged2e \
      geometry \
      xcolor \
      hyperref \
      tikzfill \
      moderncv \
      lato \
      pdfx \
      fontaxes \
      fontawesome5 \
      textpos \
      isodate \
      substr \
      xmpincl \
      paracol \
      roboto \
      simpleicons \
      academicons \
      cmap \
      accsupp \
      dashrule \
      multirow \
      adjustbox \
      collectbox \
      biber \
      biblatex \
      csquotes \
      changepage \
      biblatex-ieee \
      biblatex-apa \
      biblatex-apa6 \
      arydshln
## installing NodeJS

## we will be doing this later for live rendering of the  .tex

RUN apk add --no-cache nodejs npm fontconfig && \
    mkdir -p /usr/share/fonts/texlive && \
    ln -s /usr/local/texlive/texmf-dist/fonts/opentype /usr/share/fonts/texlive/opentype && \
    ln -s /usr/local/texlive/texmf-dist/fonts/truetype /usr/share/fonts/texlive/truetype && \
    fc-cache -fv

WORKDIR /app
COPY package*.json ./
RUN npm install --omit=dev
COPY src ./src

EXPOSE 3000
ENV PORT=3000
ENV logger_level=debug

CMD ["node", "src/index.js"]