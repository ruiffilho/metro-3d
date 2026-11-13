# Metrô 3D — instruções para o Claude

Mapa 3D (MapLibre + deck.gl + OpenFreeMap) com trens animados pelos horários GTFS oficiais.
Site: https://ruiffilho.github.io/metro-3d/ (GitHub Pages, ramo `main`, raiz). Responder ao Rui em português.

## Estrutura
- `index.html` — gerado por `pipeline/build.py` a partir de `pipeline/template.html`. **Nunca editar à mão.**
  O `build.py` põe `?v=<hash dos dados>` nos fetch de dados e sons, para o navegador não usar arquivos antigos do cache.
- `data/<cidade>.json` — dados finais de cada cidade (carregados só quando a cidade é escolhida).
- `audio/<cidade>.mp3` — aviso sonoro do metrô de cada cidade (copiado de `pipeline/chimes/`).
- `pipeline/` — scripts: `osm_route.js` + `make_route.py` + `enc_to_segs.py` (geometria pelo OSM),
  `cluster.py`, `fixjoin.py`, `lanes_gen.py` (emendas e faixas lado a lado), `qa.js` (verificação), `plot2.py` (imagem de conferência).
- `pipeline/cities/<cidade>/` — preparação específica (GTFS → JSON) e `enc/all.txt` (rotas OSM exportadas).

## Antes de todo push (obrigatório)
1. `python3 pipeline/build.py`
2. `node pipeline/qa.js` — **não publicar se der FALHA.**
3. Depois do push, abrir o site no Chrome do Rui (Claude in Chrome) com `?v=<n>` para furar o cache,
   ler o console (`read_console_messages`, só erros) e tirar um screenshot de perto (zoom ~16, prédios 3D).
   O Pages leva ~1 min para atualizar; o navegador pode guardar a versão antiga por até 10 min.

## Problemas recorrentes (já resolvidos — não repetir)
- **Linhas retas, saltos, ganchos, trens "no meio do nada"**: nunca usar `shapes.txt` do GTFS de metrô/trem
  (SPTrans e Metrovalencia têm shapes ruins). Rotear sempre pelos trilhos do OSM (`osm_route.js`),
  separando famílias (metrô ≠ trem ≠ ligeiro/elétrico ≠ monotrilho). Não usar o "re-roteamento por nó canônico" (gerou desvios 10×).
  Exceção aceitável: elétricos de rua (Carris) — shapes do GTFS ficaram bons.
- **Pedaços de linha faltando / emendas abertas nas estações**: rodar `cluster.py` e depois `fixjoin.py`.
- **Linhas sobrepostas, 4 viram 3, faixas se cruzando**: `lanes_gen.py <json> <lat> 30 1 6 1` (presença por ponto
  físico, orientação de corredor, ordem que minimiza cruzamentos, suavização e corredor comum). Valencia usa `14 0 3 0`.
- **Espessura irregular / linhas tracejadas**: deck.gl com `parameters: NODEPTH` (depthCompare always), cada trecho
  desenhado uma vez, largura uniforme. Painel sempre acima do mapa (z-index).
- **Página pesada**: `compactGeom` (Douglas-Peucker 1,5 m) e conjunto de trens ativos atualizado a cada 5 min simulados.
- **Elétricos/paragens dos dois lados da rua**: juntar paragens de mesmo nome a < 200 m num só ponto.
- **Nomes de estação só com muito zoom** (cada linha com parada própria): prioridade do rótulo pelo número de linhas
  com o mesmo nome de estação.
- **Contagem de trens irreal**: conferir com dados reais (pesquisa). Em São Paulo o `frequencies.txt` tem intervalos de pico o dia
  todo e tempos de viagem lentos demais — foram recalibrados (ver `cities/sao-paulo`). `qa.js` mostra a contagem por hora.
- **Legenda cortada**: legenda agrupada por tipo de transporte (título clicável liga/desliga o grupo), só nome da linha no item.
- **Site em branco / nada funciona**: script principal tem de ser `async function` (dados via `fetch`); `qa.js` verifica.
- **Mapa sem ruas detalhadas / sem prédios**: falha temporária do OpenFreeMap ("Failed to fetch") ou cache antigo.
  O mapa tenta recarregar os blocos sozinho a cada 5 s; testar com `?v=<n>`.
- Erro de estilo MapLibre "Only one zoom-based step or interpolate": `interpolate` por fora, `match` por dentro.
- `CollisionFilterExtension` do deck.gl faz todos os rótulos sumirem — não usar.

## Adicionar uma cidade
1. GTFS: preferir o Mobility Database (mobilitydatabase.org). O Rui baixa e envia; a rede do sandbox não acessa sites externos.
2. Preparar (`pipeline/cities/<id>/prep_<id>.py`, ver Lisboa como modelo): só os modos pedidos, cores oficiais, nomes com acento,
   serviços dia útil/sábado/domingo, `pl.json` com pares de estações por linha e família.
3. Rotear no Chrome do Rui: `python3 pipeline/make_route.py pl.json "S,O,N,L" <lat>`, colar numa aba do overpass-api.de,
   esperar `window.ST` com `done`, exportar `window.ENC` em pedaços de 980 caracteres (separados por `@@@` em raw.txt)
   e conferir com `window.HASH` usando `enc_to_segs.py`.
4. `cluster.py`, `fixjoin.py`, `lanes_gen.py`; gerar imagem com `plot2.py` e olhar.
5. Adicionar em `CITY_CFG` do template (nome, país, fuso, centro, vistas; `geral` com pitch 0) e no seletor de países;
   copiar o mp3 para `pipeline/chimes/<id>.mp3`. Depois seguir "Antes de todo push".

## Commits
Autor: `Rui dos Santos Ferreira Filho <ruiffilho@users.noreply.github.com>`. Push com `git -c push.negotiate=true push`.
