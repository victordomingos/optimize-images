[English](https://github.com/victordomingos/optimize-images/blob/master/docs/docs_EN.md) |
**[Portugu&ecirc;s](https://github.com/victordomingos/optimize-images/blob/master/docs/docs_PT.md)**

# Optimize Images [![Github commits (since latest release)](https://img.shields.io/github/commits-since/victordomingos/optimize-images/latest.svg)](https://github.com/victordomingos/optimize-images)

Um utilitário de linha de comandos escrito em Python para ajudar a reduzir o tamanho de ficheiros de imagens.

Esta aplicação é escrita tanto quanto possível em Python puro, sem requisitos técnicos especiais para além do Pillow e
do watchdog, assegurando deste modo a compatibilidade com um vasto leque de sistemas. Caso não tenha a necessidade de
uma gestão de dependências tão rigorosa, encontrará provavelmente várias outras ferramentas de otimização de imagem mais
robustas e mais avançadas, baseadas em alguns binários executáveis externos bem conhecidos.

Podem ser adicionadas algumas funcionalidades que requeiram a presença de pacotes de terceiros não escritos em Python
puro, sendo que esses pacotes serão tratados como opcionais, tais como as funcionalidades que deles dependam.

![optimize-images - captura de imagem](https://user-images.githubusercontent.com/18650184/42172232-5788c43a-7e13-11e8-8094-5811e7fd55c1.png)

## Conteúdo

* **[Instalação e dependências](#instalação-e-dependências)**

* **[Como utilizar](#como-utilizar)**
    * [Advertência](#advertência)
    * [Exemplos de utilização básica](#exemplos-de-utilização-básica)
    * [Obter ajuda sobre como usar esta aplicação](#obter-ajuda-sobre-como-usar-esta-aplicação)
    * [Opções independentes do formato](#opções-independentes-do-formato)
        - [Redimensionamento de imagens](#redimensionamento-de-imagens)
        - [Modo rápido](#modo-rápido)
        - [Monitorizar pasta pela criação de novos ficheiros](#monitorizar-pasta-pela-criação-de-novos-ficheiros)
        - [Número máximo de tarefas em simultâneo](#número-máximo-de-tarefas-em-simultâneo)
        - [Configuração de saída](#configuração-de-saída)
        - [Controlo de qualidade SSIM](#controlo-de-qualidade-ssim)
    * [Opções específicas para cada formato](#opções-específicas-para-cada-formato)
        - [JPEG](#jpeg)
            - [Qualidade](#qualidade)
            - [Manter dados EXIF](#manter-dados-exif)
        - [PNG](#png)
            - [Reduzir o número de cores](#reduzir-o-número-de-cores)
            - [Número máximo de cores](#número-máximo-de-cores)
            - [Conversão automática de imagens PNG grandes (para JPEG ou WebP)](#conversão-automática-de-imagens-png-grandes-para-jpeg-ou-webp)
            - [Mudar a cor de fundo predefinida](#mudar-a-cor-de-fundo-predefinida)
        - [WebP](#webp)
            - [Qualidade WebP](#qualidade-webp)
            - [WebP sem perdas](#webp-sem-perdas)
            - [Método WebP (esforço de compressão)](#método-webp-esforço-de-compressão)
    * [Outras funcionalidades](#outras-funcionalidades)

* **[Utilização programática (como biblioteca)](#utilização-programática-como-biblioteca)**
    * [Otimizar uma única imagem](#otimizar-uma-única-imagem)
    * [Otimizar uma pasta (em fluxo)](#otimizar-uma-pasta-em-fluxo)
    * [Otimizar uma pasta (agregado)](#otimizar-uma-pasta-agregado)
    * [Monitorizar uma pasta](#monitorizar-uma-pasta)
    * [Opções e resultados](#opções-e-resultados)
    * [Notas](#notas)

* **[Projetos relacionados](#projetos-relacionados)**
    * [Optimize Images Docker](#optimize-images-docker)
    * [Optimize Images X](#optimize-images-x)

- **[Encontrou um bug ou tem uma sugestão?](#encontrou-um-bug-ou-tem-uma-sugestão)**

## Instalação e dependências:

Para executar esta aplicação é necessária uma instalação do Python 3.10 ou superior. Procuramos manter no mínimo as
dependências externas, de modo a manter a compatibilidade com diferentes plataformas. Neste momento, requer:

- Pillow==12.0.0
- watchdog==6.0.0

A forma mais simples de instalar num único passo esta aplicação, incluindo quaisquer requisitos, é através deste
comando:

```
pip3 install pillow watchdog optimize-images
```

## Instalar a versão mais recente em desenvolvimento (possivelmente instável):

Depois de clonar este repositório, a versão atual de desenvolvimento pode ser facilmente instalada com o comando
`pip install -e`, seguido do caminho para a pasta principal do projeto (a mesma pasta que contém o ficheiro `setup.py`).
Em alternativa, poderá criar um ambiente virtual e utilizar de seguida o seguinte comando, substituindo `python3.10`
pela versão pretendida do Python 3:

```
python3.10 -m pip install git+https://github.com/victordomingos/optimize-images
```

## Como utilizar

A forma mais simples de utilização consiste na introdução de um comando simples na linha de comandos, passando o caminho
para uma imagem ou uma pasta contendo imagens como argumento.

Os argumentos opcionais `-nr` ou `--no-recursion` dizem à aplicação para não percorrer de forma recursiva todas as
subpastas (ou seja, processar imagens apenas na raiz da pasta indicada).

Por defeito, esta ferramenta aplica compressão com perdas a ficheiros JPEG utilizando um valor de qualidade variável
(entre 75 e 80), determinado de forma dinâmica para cada imagem segundo a quandidade de alteração causada nos seus
pixels, removendo seguidamente quaisquer metadados EXIF existentes. Tenta ainda otimizar as definições de cada
encodificador para a máxima redução de espaço e aplica a compressão ZLIB máxima em ficheiros PNG.

É necessário indicar explicitamente o caminho para o ficheiro de imagem original ou para a pasta que contém as imagens a
processar. Por defeito, a aplicação irá percorrer recursivamente todas as subpastas e processar quaiquer imagens
encontradas utilizando as configurações predefinidas ou as indicadas pelo utilizador, substituindo cada ficheiro
original pela sua versão processada se o seu tamanho de ficheiro for menor que o original.

Se para um determinado ficheiro não tiver sido obtida qualquer poupança de espaço, será antes mantida a versão original.

Para além das configurações predefinidas, poderá reduzir o tamanho das imagens, fazendo-as ajustarem-se à largura e/ou à
altura máxima(s) pretendida(s). Este redimensionamento de imagens é realizado como o primeiro passo no processo de
otimização de imagem.

Também poderá optar por manter os dados EXIF originais (se existirem) nos ficheiros otimizados. De notar, contudo, que
esta opção apenas se encontra disponível para ficheiros JPEG e WebP.

Nos ficheiros PNG, conseguirá alcançar uma redução mais acentuada no tamanho dos ficheiros se optar por reduzir o número
de cores utilizando uma paleta adaptativa. Tenha em consideração que ao usar esta opção a qualidade de imagem poderá ser
afetada de forma bastante notória.

Desde a versão 1.3.5, a aplicação Optimize Images oferece suporte experimental para imagens no formato MPO, as quais são
tratadas como ficheiros JPEG de imagem única (caso um ficheiro MPO contenha várias imagens, apenas a primeira será
processada).

Desde a versão 2.1.0, as imagens WebP também são otimizadas: os ficheiros WebP existentes são recodificados no próprio
local para reduzir o seu tamanho e as imagens PNG podem, opcionalmente, ser convertidas para WebP em vez de JPEG. Os
ficheiros WebP e PNG animados são deixados intactos, para evitar perder a animação.

### ADVERTÊNCIA

**Por favor, tenha em consideração que a operação deste programa é feita DE MODO DESTRUTIVO, substituindo os ficheiros
originais pelos ficheiros processados. Deverá por isso começar sempre por duplicar o ficheiro ou a pasta original antes
de usar este utilitário, de forma a poder recuperar algum ficheiro eventualmente danificado ou quaisquer imagens
resultantes que não tenham a qualidade desejada.**

### Exemplos de utilização básica

Tentar otimizar um único ficheiro:

```
optimize-images filename.jpg
```

Tentar otimizar todos os ficheiros de imagem na pasta de trabalho atual e em todas as suas subpastas:

```
optimize-images ./
```

Tentar otimizar todos os ficheiros de imagem na pasta atual, sem recursão:

```
optimize-images -nr ./
```

```
optimize-images --no-recursion ./
```

### Obter ajuda sobre como usar esta aplicação

Para consultar a lista de opções disponíveis e o seu modo de funcionamento, basta utilizar um dos seguintes comando:

```
optimize-images -h
```

```
optimize-images --help
```

### Opções independentes do formato:

#### Modo rápido:

Algumas operações poderão eventualmente ser efetuadas mais rapidamente utilizando esta opção. De um modo geral, isso
significa que os ficheiros resultantes serão um pouco maiores, para permitir em vez disso poupar alguns segundos durante
o processamento das imagens. A utilização desta opção desativa a definição de qualidade JPEG variável.

Tentar otimizar todos os ficheiros de imagem na pasta de trabalho atual, de forma recursiva, utilizando o modo rápido:

```
optimize-images -fm ./
```

```
optimize-images --fast-mode ./
```

#### Redimensionamento de imagens:

Estas opções serão aplicadas individualmente a cada imagem a ser processada. O tamanho de qualquer imagem que tenha uma
dimensão superior ao valor correspondente especificado será reduzido, sendo esse o primeiro passo de otimização. O
redimensionamento não terá efeito se, após todo o processo de otimização, o tamanho do ficheiro resultante não for
inferior ao original. Estas opções encontram-se desativadas por defeito.

Os seguintes argumentos opcionais podem ser utilizados para limitar o tamanho final das imagens:

* Largura máxima: `-mw`
* Altura máxima: `-mh`

O tamanho da imagem será reduzido para o tamanho máximo que caiba dentro da Largura e/ou altura especificada(s). Se o
utilizador introduzir valores para ambas as dimensões, serão calculadas as proporções da imagem para cada caso e será
aplicada a que resulte num tamanho menor.

Tentar otimizar todos os ficheiros de imagem na pasta de trabalho atual, de forma recursiva, reduzindo o tamanho de cada
imagem para uma larga máxima de 1600 pixels:

```
optimize-images -mw 1600 ./
```

Tentar otimizar todos os ficheiros de imagem apenas na raiz da pasta de trabalho atual, de forma não recursiva,
reduzindo o tamanho de cada imagem para uma altura máxima de 800 pixels:

```
optimize-images -nr -mh 800 ./
```

#### Monitorizar pasta pela criação de novos ficheiros:

Utilize esta opção quando tiver uma pasta onde pretenda monitorizar o aparecimento de novos ficheiros de imagem e
processá-los logo que possível. A aplicação Optimize Images irá vigiar a pasta especificada de forma contínua e
otimizará de forma autmática qualquer ficheiro acabado de criar. Os caminhos dos ficheiros são guardados numa lista
temporária em memória, de modo a que cada ficheiro seja processado uma única vez por sessão.

Geralmente, os ficheiros que já existam quando inicia Optimized Images com esta opção não serão processados, mas é
possível forçar esse processamento. Para tal, basta usar dois comandos consecutivos: primeiro, uma passagem normal sem o
argumento `-wd`, para processar os ficheiros existentes; depos, uma segunda chamada, desta vez já com o argumento `-wd`,
para continuar a vigiar a pasta e processar quaisquer novos ficheiros à medida que forem criados.

```
optimize-images -wd ./
```

```
optimize-images --watch-directory ./
```

Esta funcionalidade utiliza o pacote `watchdog` (uma dependência principal), fornecido por terceiros, bem como as suas
respetivas dependências, e está disponível apenas nos sistemas operativos suportados por ele. Não está disponível, por
exemplo, em iOS.

Neste momento, ao utilizar esta funcionalidade, não se encontra disponível a execução com multiprocessamento.

#### Número máximo de tarefas em simultâneo

É possível especificar o número máximo de tarefas de processamento a executar em simultâneo. O valor predefinido (0), na
maior parte das plataformas, irá gerar um total de N + 1 processos, em que N é o número de processadores ou núcleos
presentes no sistema.

```
optimize-images -jobs 16 ./
```

#### Configuração de saída

Para especificar o texto a apresentar, podem ser utilizadas estas opções opcionais:

##### Modo Silencioso

Com a opção `--quiet`, não verá qualquer saída de texto, excepto as mensagens de erro e excepções que possam ocorrer
durante o processo de otimização.

```
optimize-images --quiet ./
```

##### Mostrar apenas o resumo

Ao usar esta opção, não haverá nenhuma saída durante de texto durante a otimização. Apenas será apresentado o resumo
quando terminar.

```
optimize-images --only-summary ./
```

##### Mostrar apenas o progresso

Isto apenas mostrará o progresso geral e não o resultado da optimização de cada ficheiro.

```
$ optimize-images --only-progress ./
... 
[14.0s 57.1%] ✅ 18 🔴 68, saved 44.1 MB
...
```

#### Controlo de qualidade SSIM

O índice de semelhança estrutural (SSIM) mede quão próximo do aspeto da imagem imediatamente antes da codificação final
com perdas está o resultado codificado, numa escala entre 0 e 1, em que 1 significa indistinguível. A referência é uma
cópia da imagem feita *depois* de todas as transformações, pelo que a pontuação reflete apenas a perda da codificação
final ou da conversão de formato: opções como a redução de tamanho (`-mw`/`-mh`), a redução de cores (`-rc`) e a
conversão para escala de cinzentos (`-g`) não a diminuem. Aplica-se a JPEG, WebP e à conversão de formato, e requer o
pacote opcional scikit-image (instale-o com `pip install scikit-image` ou `pip install optimize-images[ssim]`). Note
que, para ficheiros PNG que não são convertidos para outro formato, a codificação é sem perdas, pelo que a pontuação é
sempre 1.0000 e o limite nunca os pode rejeitar. Para imagens com transparência, a pontuação é calculada sobre a cor de
fundo (`-bg`/`-hbg`, branco por omissão).

Use `-ssm` ou `--ssim-min LIMITE` para manter o ficheiro original sempre que o resultado pontuar abaixo do limite (um
decimal entre 0 e 1, por exemplo 0.95). O limite é verificado *depois* da codificação: não altera nunca a qualidade
usada pelo codificador (seleção de qualidade dinâmica, um `-q` fixo ou as definições de conversão) — apenas decide se o
resultado codificado é mantido. Um resultado é mantido somente quando é ao mesmo tempo pelo menos 1% mais pequeno do que
o original (menos de 99% do seu tamanho) e com pontuação igual ou superior ao limite; com `-nc` (comparação de tamanho
desativada), aplica-se apenas o limite. Se a pontuação não puder ser calculada para um ficheiro, o original é mantido
por precaução; por isso, definir `--ssim-min 0` não desativa o controlo: os ficheiros sem pontuação continuam a ser
rejeitados. Para o desativar, omita a opção. Sem o scikit-image, esta opção interrompe a execução com uma mensagem de
erro clara.

Os intervalos recomendados diferem conforme o regime. Medido em 224 fotografias com o codificador por omissão atual
(qualidade dinâmica, ajustada para a web), as pontuações in situ variaram entre 0.929 e 1.0 (mediana 0.981): 0.90 não
rejeita nada, e os valores úteis são **0.93-0.97** — a rejeição começa acima de 0.92 e cresce depressa (0.95 rejeita
cerca de 2,2% dos ficheiros, em torno de 2,5% do total das poupanças de espaço; 0.96 cerca de 5,5%; 0.97 cerca de
17,6%). As pontuações de conversão são mais baixas: 0.95 rejeita 16,6% dos ficheiros com `-ca` e 32,3% com
`-ca -cc webp`, pelo que os valores úteis aí são **0.85-0.93**. A opção fica desativada por omissão; ative-a com
`--ssim-min` quando quiser essa garantia.

A pontuação é calculada com a função `structural_similarity` do scikit-image, que usa por omissão uma janela uniforme de
7x7, em vez da janela gaussiana do artigo original do SSIM, pelo que as pontuações podem ser ligeiramente mais altas
(cerca de 0.004) do que as de ferramentas que usam a versão gaussiana. Os limites recomendados acima foram calibrados
com esta implementação.

Calcular a pontuação é dispendioso: pode dominar o tempo de execução em pastas com imagens muito grandes, pelo que uma
execução com SSIM ativado levará muito mais tempo do que sem ele.

```
optimize-images --ssim-min 0.95 ./
```

Use `--show-ssim` (ou `--no-show-ssim` para a forçar desativada) para mostrar a pontuação SSIM calculada de cada
ficheiro no relatório. A pontuação é mostrada automaticamente sempre que `--ssim-min` for usado; sem o scikit-image,
`--show-ssim` mostra um aviso uma vez e nenhuma pontuação é exibida. A `--no-show-ssim` oculta apenas as pontuações
dos ficheiros otimizados: um ficheiro rejeitado porque a sua pontuação ficou abaixo do limite continua a ser reportado
com a pontuação e o limite. Os ficheiros otimizados aparecem com a pontuação na linha de pormenores; os reportados como
ignorados mostram-na numa segunda linha apenas quando o limite os rejeitou — assinalado com o limite — para se manterem
distinguíveis dos ficheiros ignorados apenas por não serem mais pequenos (os ficheiros sem pontuação, como os WebP e
PNG animados, são reportados como ignorados).

```
optimize-images --show-ssim ./
```

### Opções específicas para cada formato:

As seguintes definições específicas para cada formato são opcionais e podem ser utilizadas simultaneamente- por exemplo
ao processar uma pasta que poderá conter imagens em mais do que um formato. As definições específicas introduzidas pelo
utilizador serão então selecionadas e aplicadas automaticamente para cada imagem.

#### JPEG:

##### Qualidade

Defina a qualidade para ficheiros JPEG (um número inteiro, entre 1 e 100), usando o argumento `-q`, seguido do valor de
qualidade a aplicar. Um valor mais baixo reduzirá tanto a qualidade de imagem como o tamanho do ficheiro. A utilização
desta opção desativa a definição de qualidade variável.

Tentar otimizar todos os ficheiros de imagem na pasta de trabalho atual e em todas as subpastas, aplicando uma qualidade
de 65% aos ficheiros JPEG:

```
optimize-images -q 65 ./
```

##### Manter dados EXIF

Utilize a opção `-ke` ou `--keep-exif` para manter os dados EXIF existentes em imagens JPEG e WebP (por defeito, se não
acrescentar este argumento, os dados EXIF são apagados.

Tentar otimizar todos os ficheiros de imagem na pasta de trabalho atual e em todas as suas subpastas, aplicando uma
qualidade de 65% a ficheiros JPEG e mantendo os dados EXIF originais:

```
optimize-images -q 65 -ke ./
```

#### PNG:

##### Reduzir o número de cores

Para reduzir o número de cores (PNG) usando uma paleta de cores adaptativa Com difusão, utilize o argumento opcional
`-rc`. Esta opção pode ter um grande impacto no tamanho dos ficheiros, mas por favor tenha em consideração que também
irá afetar de uma forma muito notória a qualidade de imagem, especialmente em imagens que tenham gradientes de cores
e/ou transparência.

Tentar otimizar um único ficheiro de imagem na pasta atual, aplicando uma paleta de cores adaptativa, com o número de
cores predefinido (255):

```
optimize-images -rc ./imagefile.png
```

##### Número máximo de cores

Utilize o argumento opcional `-mc` para especificar o Número máximo de cores para imagens PNG, ao utilizar a opção de
redução de cores (um número inteiro entre 0 e 255). O valor predefinido é 255.

Tentar otimizar um único ficheiro de imagem na pasta atual, reduzindo a paleta de cores para um valor específico:

```
optimize-images -rc -mc 128 ./imagefile.png
```

Tentar otimizar todos os ficheiros de imagem na pasta atual e em todas as suas subpastas, aplicando uma qualidade de 65%
aos ficheiros JPEG e reduzindo a paleta de cores dos ficheiros PNG para apenas 64 cores:

```
optimize-images -q 60 -rc -mc 64 ./
```

Convém notar que se for indicado um número de cores muito baixo isso pode implicar a perda de transparência,
substituindo-a por cores inesperadas. Nesses casos, é normalmente possível obter melhores resultados utilizando esta
opção combinada com a remoção explícita de transparência (`-rt`) e com a substituição da cor de fundo (`-bg` ou `-hbg`).

Por exemplo, para otimizar um ficheiro PNG, reduzindo a paleta para o máximo de 8 cores, removendo a transparência e
aplicando um fundo branco:

```
optimize-images -rc -mc 8 -rt -hbg ffffff ./imagefile.png
```

##### Conversão automática de imagens PNG grandes (para JPEG ou WebP)

Converter automaticamente quaisquer imagens PNG grandes que tenham um grande número de cores (presumivelmente uma
fotografia ou uma imagem semelhante a uma fotografia) para um formato mais eficiente. Utiliza um algoritmo para
determinar se a conversão vale a pena e decide automaticamente sobre isso. Use
`-cb` (ou `--convert-big`) para esta seleção automática (específica de PNG fotográficos grandes), ou `-ca` (ou
`--convert-all`) para converter todas as imagens encontradas, independentemente do formato de origem. Por defeito, os
ficheiros originais permanecem intactos e são mantidos juntamente com as imagens convertidas, nas pastas originais.

O formato de destino da conversão é JPEG por defeito. Use `-cf` (ou
`--convert-to FORMATO`) para escolher outro formato de saída. Os destinos disponíveis dependem dos codecs compilados na
build do Pillow em uso (tipicamente `jpeg`, `png`, `webp`, `avif` e `jpeg2000`); corra com `-h` para ver as opções no
seu sistema. Ao contrário do JPEG, formatos como WebP, AVIF e PNG mantêm qualquer transparência.

A conversão respeita a comparação de tamanhos tal como a otimização normal: o ficheiro convertido só é mantido quando
fica de facto pelo menos 1% mais pequeno do que o original (menos de 99% do seu tamanho), a menos que desative a
comparação com `-nc`. É isto que torna seguro pedir qualquer destino - se não poupar espaço, é simplesmente ignorado.

**IMPORTANTE: SE JÁ EXISTIR UM FICHEIRO COM O MESMO NOME E A EXTENSÃO DE DESTINO, SERÁ SUBSTITUÍDO PELO FICHEIRO
RESULTANTE DESTA CONVERSÃO.**

```
optimize-images -cb ./
```

Converter todas as imagens para WebP em vez de JPEG:

```
optimize-images -ca --convert-to webp ./
```

Para forçar o apagamento dos ficheiros PNG originais ao converter, adicione o argumento `-fd` ou `--force-delete`:

```
optimize-images -cb -fd ./
```

##### Mudar a cor de fundo predefinida

Por defeito, ao remover a transparência ou ao converter de PNG para JPEG, será aplicado um fundo branco. É possível
escolher uma cor de fundo diferente usando o argumento `-bg` seguido de 3 números inteiros, separados por espaços, entre
0 e 255, para Vermelho, Verde e Azul (RGB). Por exemplo: `255 0 0` (para aplicar um vermelho vivo).

Para converter uma imagem PNG grande com alguma transparência (como, por exemplo, capturas de ecrã do macOS) aplicando
um fundo preto:

```
optimize-images -cb -bg 0 0 0 ./image.png
```

Se preferir utilizar valores hexadecinais, como os que são usados normalmente no código HTML, poderá utilizar em
alternativa o argumento `-hbg`
seguido do código da cor sem o cardinal (#). Por exemplo:
`00FF00` para uma cor verde pura e viva.

Para converter uma imagem PNG grande com alguma transparência aplicando um fundo verde puro:

```
optimize-images -cb -hbg 00FF00 ./image.png
```

#### WebP:

Os ficheiros de imagem WebP existentes são otimizados alterando os ficheiros originais, recodificando-os com as
definições abaixo. O WebP mantém a transparência (canal alfa), exceto se também pedir para a remover com `-rt`. Os
ficheiros WebP e PNG animados são detetados e deixados intactos, para evitar perder a animação.

Também pode converter imagens PNG para WebP em vez de JPEG - consulte
[Conversão automática de imagens PNG grandes (para JPEG ou WebP)](#conversão-automática-de-imagens-png-grandes-para-jpeg-ou-webp).

##### Qualidade WebP

Defina a qualidade para ficheiros WebP (um número inteiro entre 1 e 100) usando o argumento `-wq`.
O valor predefinido é 80. Um valor mais baixo reduz tanto a qualidade de imagem como o tamanho do ficheiro. No modo sem
perdas (ver abaixo), este valor controla antes o esforço de compressão.

Tentar otimizar todos os ficheiros WebP na pasta atual com uma qualidade de 75:

```
optimize-images -wq 75 ./
```

##### WebP sem perdas

Utilize o argumento `-wl` ou `--webp-lossless` para codificar imagens WebP em modo sem perdas. Isto preserva exatamente
todos os pixels, mas para imagens fotográficas resulta normalmente em ficheiros muito maiores do que o modo com perdas.

```
optimize-images -wl ./
```

##### Método WebP (esforço de compressão)

Utilize o argumento `-wm` para definir o método de compressão WebP, um número inteiro entre 0 e 6, em que 6 é o mais
lento mas costuma dar a melhor compressão. O valor predefinido é 6.

```
optimize-images -wm 4 ./
```

### Outras funcionalidades

Consultar o número da versão instalada deste programa:

```
optimize-images -v
```

```
optimize-images --version
```

Consultar a lista das extensões usuais dos vários formatos de imagem atualmente suportados (note, por favor, que as
imagens que não tenham no nome de ficheiro a extensão correta correspondente ao seu formato serão ignoradas):

```
optimize-images -s
```

```
optimize-images --supported
```

Para inspecionar uma única imagem e imprimir os seus metadados — formato, modo, dimensões, transparência, tamanho da
paleta, indicadores progressivo/entrelaçado, número de fotogramas, DPI, perfil ICC e EXIF — use a opção `-i`/`--info`:

```
optimize-images -i foto.jpg
```

```
optimize-images --info foto.jpg
```

### Utilização programática (como biblioteca)

Desde a versão 2.0.0, o pacote disponibiliza uma API estável, sem interface gráfica, no módulo `optimize_images.api`,
para integrar a lógica de otimização nas suas próprias aplicações. Dê-lhe preferência em relação aos módulos de mais
baixo nível, que são internos e podem mudar sem aviso.

#### Otimizar uma única imagem

```python
from optimize_images.api import optimize_single_image

result = optimize_single_image("photo.jpg", quality=70, max_w=1920)
print(result.was_optimized, result.orig_size, result.final_size)
```

As opções são apenas por palavra-chave: `quality`, `max_w`, `max_h`, `reduce_colors`, `max_colors`,
`remove_transparency`, `bg_color`, `grayscale`, `keep_exif`, `convert_all`, `conv_big`, `force_del`, `fast_mode`,
`ignore_size_comparison`, `convert_to`, `webp_quality`, `webp_lossless`, `webp_method`, `ssim_min`, `show_ssim`. O
formato de destino da conversão é definido por `convert_to` (`'jpeg'` por defeito, ou `'webp'`); a codificação WebP é
ajustada com `webp_quality`, `webp_lossless` e `webp_method`. O `ssim_min` mantém o ficheiro original quando o resultado
pontua abaixo do mínimo de semelhança estrutural, e o `show_ssim` pede a pontuação calculada no resultado; ambos
dependem do pacote opcional scikit-image. Quando apenas `ssim_min` é dado (`show_ssim` é `False`), os resultados
rejeitados por não serem pelo menos 1% menores não são pontuados (`ssim` é `None`), e `show_ssim`
devolve sempre a pontuação.

#### Otimizar uma imagem em memória (bytes a entrar, bytes a sair)

Quando as imagens estão guardadas como dados binários em vez de ficheiros — por exemplo num sistema de gestão de
conteúdos, num object store ou numa base de dados — e não há um caminho de ficheiro disponível, use
`optimize_image_data`. Recebe os bytes da imagem e devolve os bytes otimizados juntamente com um objeto de resultado:

```python
from optimize_images.api import optimize_image_data

otimizada, resultado = optimize_image_data(bytes_originais, quality=70, max_w=1920)
if resultado.was_optimized:
    guardar(otimizada)   # imagem mais pequena; caso contrário é a original
```

Mantém o formato original e aceita as mesmas opções de processamento que o
`optimize_single_image`, exceto as específicas de ficheiro/conversão: `quality`,
`max_w`, `max_h`, `reduce_colors`, `max_colors`, `remove_transparency`,
`bg_color`, `grayscale`, `keep_exif`, `fast_mode`, `ignore_size_comparison`,
`webp_quality`, `webp_lossless`, `webp_method`, `ssim_min`, `show_ssim`, e ainda um `name` opcional que é devolvido no
resultado. Quando otimizar não compensa (e a comparação de tamanho não foi desativada), os bytes originais são
devolvidos inalterados. A conversão de formato não é suportada por este ponto de entrada.

#### Converter uma imagem em memória (bytes a entrar, bytes a sair)

O equivalente em memória da conversão de formato, para os mesmos casos de quem só tem dados binários. A
`convert_image_data` converte os bytes para outro formato e devolve os bytes convertidos mais o formato resultante:

```python
from optimize_images.api import convert_image_data

bytes_webp, resultado = convert_image_data(bytes_png, to="webp", webp_quality=80)
if resultado.was_optimized:
    guardar(bytes_webp, content_type="image/" + resultado.result_format.lower())
```

`to` é o formato de destino (`'jpeg'`, `'png'`, `'webp'`, e `'avif'` ou
`'jpeg2000'` quando o Pillow os suportar), validado contra os codecs realmente disponíveis. Verifique sempre
`resultado.result_format` para saber o formato dos bytes devolvidos: quando converter não reduz o tamanho (e a
comparação não foi desativada), são devolvidos os bytes e o formato **originais** inalterados; converter para o próprio
formato da origem otimiza-a no lugar; e fontes multi-fotograma (animações) são devolvidas inalteradas. Aceita as opções
comuns
`quality`, `max_w`, `max_h`, `remove_transparency`, `bg_color`, `grayscale`,
`keep_exif`, `ignore_size_comparison`, `webp_quality`, `webp_lossless`,
`webp_method`, `ssim_min`, `show_ssim`, e um `name` opcional.

#### Otimizar uma pasta (em fluxo)

Devolve cada resultado à medida que é processado — ideal para indicar o progresso:

```python
from optimize_images.api import PublicBatchOptions, optimize_as_batch_stream

options = PublicBatchOptions(src_path="./images", quality=75, jobs=4)
for r in optimize_as_batch_stream(options):
    print(r.img, "poupou", r.orig_size - r.final_size, "bytes")
```

#### Otimizar uma pasta (agregado)

Bloqueia e devolve os totais:

```python
from optimize_images.api import PublicBatchOptions, optimize_as_batch

summary = optimize_as_batch(PublicBatchOptions(src_path="./images"))
print(summary.optimized_files, "de", summary.found_files,
      "-", summary.total_bytes_saved, "bytes poupados")
```

#### Monitorizar uma pasta

```python
import threading
from optimize_images.api import PublicBatchOptions, watch_directory

stop = threading.Event()
options = PublicBatchOptions(src_path="./incoming", quality=80)
watch_directory(options, lambda r: print("otimizada:", r.img), stop)
# chamar stop.set() a partir de outra thread para terminar a monitorização
```

#### Inspecionar os metadados de uma imagem

`inspect_image(caminho)` devolve um objeto `ImageMetadata` com as propriedades intrínsecas da imagem e o respetivo EXIF
agrupado por secção de IFD (`image`,
`camera`, `gps`), com valores crus. `format_exif(metadata.exif)` é um ajudante opcional que converte esses valores crus
em texto pronto a mostrar, usando a semântica padronizada do EXIF (unidades como `f/1.8` e `50 mm`, enumerados como
`Orientation` e coordenadas de GPS combinadas).

```python
from optimize_images.api import inspect_image, format_exif

meta = inspect_image("foto.jpg")
print(meta.image_format, meta.width, meta.height, meta.has_alpha)

for seccao, tags in format_exif(meta.exif).items():
    print(seccao)
    for nome, valor in tags.items():
        print(f"  {nome}: {valor}")
```

#### Opções e resultados

`PublicBatchOptions` reúne todas as definições; apenas `src_path` é obrigatório (as predefinições incluem `quality=80`,
`recursive=True`, `jobs=0`, que significa deteção automática). Cada imagem otimizada é reportada através de um
`PublicTaskResult` com: `img`, `orig_format`/`result_format`, `orig_mode`/`result_mode`, `orig_colors`/`final_colors`,
`orig_size`/`final_size` (em bytes), `ssim` (a pontuação de semelhança estrutural, ou None quando não foi
calculada — quando apenas `ssim_min` foi dado e o ficheiro foi rejeitado pela verificação de tamanho, quando o
scikit-image está em falta e `show_ssim` foi pedido, ou quando a pontuação não foi solicitada), e os
indicadores `was_optimized`, `was_downsized`, `had_exif`, `has_exif`. A função `optimize_as_batch` devolve um
`PublicBatchResult` com a lista de ficheiros, além das contagens agregadas, do tamanho total, dos bytes poupados e do
tempo decorrido.

#### Notas

- O número de processos de trabalho é determinado automaticamente a partir da plataforma (CPU), exceto se definir
  `options.jobs` com um valor diferente de zero.
- `watch_directory` escreve uma legenda e um cabeçalho na saída padrão e utiliza o pacote `watchdog` (uma
  dependência principal); se este estiver em falta, é lançada a exceção `ImportError`.
- O SSIM só está disponível quando o pacote opcional scikit-image está instalado (ou com o extra `[ssim]`): o
  `ssim_min` lança `optimize_images.exceptions.OISSIMNotAvailableError` quando ele falta, enquanto o `show_ssim` produz
  simplesmente pontuações `None`; a CLI mostra um aviso uma vez quando `--show-ssim` foi pedido sem ele. Um `ssim_min`
  fora do intervalo 0.0-1.0 (incluindo NaN) lança `ValueError`.
- As funções `optimize_as_batch`, `optimize_as_batch_stream` e
  `optimize_single_image` lançam
  `optimize_images.exceptions.OIImagesNotFoundError` quando um caminho não corresponde a nenhuma imagem;
  `watch_directory` lança a mesma exceção quando o caminho não é uma pasta existente.

### Projetos relacionados

#### [Optimize Images Docker](https://github.com/varnav/optimize-images-docker)

Uma implementação de Optimize Images para docker, da autoria de terceiros. Inclui algumas otimizações interessantes,
como por exemplo o uso de uma versão recente da biblioteca [mozjpeg](https://github.com/mozilla/mozjpeg) ou uma versão
do Pillow compilada com a [libimagequant](https://github.com/ImageOptim/libimagequant), o que deve resultar numa
compressão ainda mais rápida e mais eficiente.

#### [Optimize Images X](https://github.com/victordomingos/optimize-images-x)

Aplicação com interface de utilizador em modo gráfico que disponibiliza todo o potencial de Optimize Images. Tal como a
versão original para linha de comandos, pode processar um ficheiro ou uma pasta de ficheiros de imagens, com opção de
incluir ou não de forma recursiva as suas subpastas. As tarefas de processamento são automaticamente distribuidas pelos
núcleos do processador. Inclui ainda a funcionalidade "watch folder", que permite monitorizar uma pasta quanto à criação
de novos ficheiros, processando-os de imediato.

## Encontrou um *bug* ou tem uma sugestão?

Por favor avise-nos, abrindo um novo *issue* ou *pull request*.