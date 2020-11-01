[English](https://github.com/victordomingos/optimize-images/blob/master/docs/docs_EN.md) | **[Portugu&ecirc;s](https://github.com/victordomingos/optimize-images/blob/master/docs/docs_PT.md)**


# Optimize Images [![Github commits (since latest release)](https://img.shields.io/github/commits-since/victordomingos/optimize-images/latest.svg)](https://github.com/victordomingos/optimize-images)
Um utilitário de linha de comandos escrito em Python para ajudar a reduzir o
tamanho de ficheiros de imagens.

Esta aplicação é escrita tanto quanto possível em Python puro, sem requisitos
técnicos especiais para além do Pillow, assegurando deste modo a
compatibilidade com um vasto leque de sistemas, incluindo iPhones e iPads com
a app Pythonista 3. Caso não tenha a necessidade de uma gestão de dependências
tão rigorosa, encontrará provavelmente várias outras ferramentas de otimização de
imagem mais robustas e mais avançadas, baseadas em alguns binários executáveis
externos bem conhecidos.


![optimize-images - captura de imagem](https://user-images.githubusercontent.com/18650184/42172232-5788c43a-7e13-11e8-8094-5811e7fd55c1.png)


## Conteúdo
* **[Instalação e dependências](#instalação-e-dependências)**
   - [Em sistemas operativos de secretária](#em-sistemas-operativos-de-secretária)
   - [Em iPhone ou iPad (na app Pythonista 3 para iOS)](#em-iphone-ou-ipad-na-app-pythonista-3-para-ios)
   
* **[Como utilizar](#como-utilizar)**
   * [Advertência](#advertência)
   * [Exemplos de utilização básica](#examplos-de-utilização-básica)
   * [Obter ajuda sobre como usar esta aplicação](#obter-ajuda-sobre-como-usar-esta-aplicação)
   * [Opções independentes do formato](#opções-independentes-do-formato)
       - [Redimensionamento de imagens](#redimensionamento-de-imagens)
       - [Modo rápido](#modo-rápido)
       - [Monitorizar pasta pela criação de novos ficheiros](#monitorizar-pasta-pela-criação-de-novos-ficheiros)
       - [Número máximo de tarefas em simultâneo](#número-máximo-de-tarefas-em-simultâneo)
   * [Opções específicas para cada formato](#opções-específicas-para-cada-formato)
       - [JPEG](#jpeg)
          - [Qualidade](#qualidade)
          - [Manter dados EXIF](#manter-dados-exif)
       - [PNG](#png)
          - [Reduzir o número de cores](#reduzir-o-número-de-cores)
          - [Número máximo de cores](#número-máximo-de-cores)
          - [Conversão automática de imagens PNG grandes para JPEG](#conversão-automática-de-imagens-png-grandes-para-jpeg)
          - [Mudar a cor de fundo predefinida](#mudar-a-cor-de-fundo-predefinida)
   * [Outras funcionalidades](#outras-funcionalidades)
   
- **[Encontrou um bug ou tem uma sugestão?](#encontrou-um-bug-ou-tem-uma-sugestão)**


## Instalação e dependências:

### Em sistemas operativos de secretária

Para executar esta aplicação é necessária uma instalação do Python 3.6 ou
superior. Procuramos manter no mínimo as dependências externas, de modo a
manter a compatibilidade com diferentes plataformas, incluindo Pythonista em
iOS. Neste momento, requer:

  - Pillow>=8.0.1
  - piexif>=1.1.3
  - watchdog>=0.10.3

A forma mais simples de instalar num único passo esta aplicação, incluindo
quaisquer requisitos, é através deste comando:

```
pip3 install pillow watchdog optimize-images
```

Caso tenha a possibilidade de substituir o Pillow pela versão mais rápida 
[Pillow-SIMD](https://github.com/uploadcare/pillow-simd), deverá conseguir
notar um desempenho consideravelmente superior. É por isso que, por cortesia,
disponibilizamos um pequeno *script* de linha de comandos opcional 
(`replace_pillow__macOS.sh`) para substituir o Pillow pelo Pillow-SIMD no 
macOS. Tenha em consideração, contudo, que isso geralmente implica um passo 
de compilação e é um processo que não testámos de forma aprofundada, pelo 
que os seus resultados podem variar.


### Em iPhone ou iPad (na app Pythonista 3 para iOS)

Primeiro, irá precisar de um ambiente Python e uma consola de linha de comandos
compatível com Python 3. No momento presente, isto significa que precisa de ter
instalada uma app chamada [Pythonista 3](http://omz-software.com/pythonista/)
(que é, entre outras coisas, um excelente ambiente para desenvolvimento e
execução de aplicações de Python puro em iOS). 

Depois, precisará de instalar a
[StaSh](https://github.com/ywangd/stash), que é uma consola de linha de
comandos baseada em Python, concebida especificamente para correr no
Pythonista. Irá permitir executar comandos bem úteis como `wget`, `git clone`,
`pip install` e muitos outros. Merece realmente um atalho no ecrã principal do
seu iPhone ou iPad. 

Depois de seguir as instruções para a instalação da StaSh,
poderá precisar de a atualizar para uma versão mais recente. Experimente este
comando:

```
selfupdate.py -f dev
```

De seguida, force o encerramento do Pythonista, reiniciando-o de seguida, e
inicie novamente a StaSh. Deverá estar agora a correr em Python 3. Neste
momento, pode tentar instalar esta aplicação, diretamente a partir deste
repositório:

```
pip install optimize-images
```

Se tudo correr bem, o comando acima deverá instalar quais quer dependências,
colocar um pacote chamado `optimize_images` dentro da pasta
`~/Documents/site-packages-3` e criar um *script* de execução chamado
`optimize-images.py` em `stash_extensions/bin`.

Neste momento, em Pythonista/iOS esta aplicação requer:

  - piexif==1.0.13


No final dos passos anteriores, force o encerramento do Pythonista, reinicie 
a app e inicie novamente a StaSh. Já deverá conseguir executar esta aplicação 
diretamente a partir da consola ou criando um atalho no ecrã inicial do iOS, 
com os argumentos necessários, para o script de entrada, localizado em 
`~/Documents/stash_extensions/bin/optimize-images.py`, para otimizar quaisquer 
ficheiros de imagem que tenha no Pythonista.


## Instalar a versão mais recente em desenvolvimento (possivelmente instável):

### Em sistemas operativos de secretária

Depois de clonar este repositório, a versão atual de desenvolvimento pode ser
facilmente instalada com o comando `pip install -e`, seguido do caminho para
a pasta principal do projeto (a mesma pasta que contém o ficheiro `setup.py`).
Em alternativa, poderá criar um ambiente virtual e utilizar de seguida o 
seguinte comando, substituindo `python3.8` pela versão pretendida do Python 3:

```
python3.8 -m pip install git+https://github.com/victordomingos/optimize-images
```

### Em iPhone ou iPad (na app Pythonista 3 para iOS)

Em iOS, depois de seguir os passos necessários à instalação do Pythonista e a
StaSh, a versão atual de desenvolvimento pode ser instalada diretamente a
partir deste repositório git:

```
pip install victordomingos/optimize-images
```

Se tudo correr bem, o comando acima deverá instalar quais quer dependências,
colocar um pacote chamado `optimize_images` dentro da pasta
`~/Documents/site-packages-3` e criar um *script* de execução chamado
`optimize-images.py` em `stash_extensions/bin`.


No final, como habitualmente, force o encerramento do Pythonista, reinicie
a app e inicie novamente a StaSh. Já deverá conseguir executar esta aplicação
diretamente a partir da consola ou criando um atalho no ecrã inicial do iOS,
com os argumentos necessários, para o script de entrada, localizado em
`~/Documents/stash_extensions/bin/optimize-images.py`, para otimizar quaisquer
ficheiros de imagem que tenha no Pythonista.



## Como utilizar

A forma mais simples de utilização consiste na introdução de um comando simples 
na linha de comandos, passando o caminho para uma imagem ou uma pasta contendo 
imagens como argumento.

Os argumentos opcionais `-nr` ou `--no-recursion` dizem à aplicação para não
percorrer de forma recursiva todas as subpastas (ou seja, processar imagens 
apenas na raiz da pasta indicada).

Por defeito, esta ferramenta aplica compressão com perdas a ficheiros JPEG 
utilizando um valor de qualidade variável (entre 75 e 80), determinado de
forma dinâmica para cada imagem segundo a quandidade de alteração causada
nos seus pixels, removendo seguidamente quaisquer metadados EXIF existentes.
Tenta ainda otimizar as definições de cada encodificador para a máxima redução
de espaço e aplica a compressão ZLIB máxima em ficheiros PNG.

É necessário indicar explicitamente o caminho para o ficheiro de imagem 
original ou para a pasta que contém as imagens a processar. Por defeito, 
a aplicação irá percorrer recursivamente todas as subpastas e processar 
quaiquer imagens encontradas utilizando as configurações predefinidas ou as
indicadas pelo utilizador, substituindo cada ficheiro original pela sua 
versão processada se o seu tamanho de ficheiro for menor que o original.

Se para um determinado ficheiro não tiver sido obtida qualquer poupança de 
espaço, será antes mantida a versão original.

Para além das configurações predefinidas, poderá reduzir o tamanho das imagens,
fazendo-as ajustarem-se à largura e/ou à altura máxima(s) pretendida(s). Este 
redimensionamento de imagens é realizado como o primeiro passo no processo de 
otimização de imagem.

Também poderá optar por manter os dados EXIF originais (se existirem) nos 
ficheiros otimizados. De notar, contudo, que esta opção apenas se encontra 
disponível para ficheiros JPEG.

Nos ficheiros PNG, conseguirá alcançar uma redução mais acentuada no tamanho 
dos ficheiros se optar por reduzir o número de cores utilizando uma paleta 
adaptativa. Tenha em consideração que ao usar esta opção a qualidade de
imagem poderá ser afetada de forma bastante notória.

Desde a versão 1.3.5, a aplicação Optimize Images oferece suporte experimental 
para imagens no formato MPO, as quais são tratadas como ficheiros JPEG de imagem 
única (caso um ficheiro MPO contenha várias imagens, apenas a primeira será 
processada).


### ADVERTÊNCIA
**Por favor, tenha em consideração que a operação deste programa é feita DE 
MODO DESTRUTIVO, substituindo os ficheiros originais pelos ficheiros 
processados. Deverá por isso começar sempre por duplicar o ficheiro ou a pasta 
original antes de usar este utilitário, de forma a poder recuperar algum 
ficheiro eventualmente danificado ou quaisquer imagens resultantes que não
tenham a qualidade desejada.**


### Exemplos de utilização básica

Tentar otimizar um único ficheiro:

```
optimize-images filename.jpg
```

  
Tentar otimizar todos os ficheiros de imagem na pasta de trabalho atual e em 
todas as suas subpastas:

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

Para consultar a lista de opções disponíveis e o seu modo de funcionamento, 
basta utilizar um dos seguintes comando:

```
optimize-images -h
```

```
optimize-images --help
```
  

### Opções independentes do formato:

#### Modo rápido:

Algumas operações poderão eventualmente ser efetuadas mais rapidamente
utilizando esta opção. De um modo geral, isso significa que os ficheiros
resultantes serão um pouco maiores, para permitir em vez disso poupar alguns
segundos durante o processamento das imagens. A utilização desta opção
desativa a definição de qualidade JPEG variável.

Tentar otimizar todos os ficheiros de imagem na pasta de trabalho atual, de
forma recursiva, utilizando o modo rápido:

```
optimize-images -fm ./
```

```
optimize-images --fast-mode ./
```


#### Redimensionamento de imagens:

Estas opções serão aplicadas individualmente a cada imagem a ser processada.
O tamanho de qualquer imagem que tenha uma dimensão superior ao valor 
correspondente especificado será reduzido, sendo esse o primeiro passo de 
otimização. O redimensionamento não terá efeito se, após todo o processo de 
otimização, o tamanho do ficheiro resultante não for inferior ao original.
Estas opções encontram-se desativadas por defeito.

Os seguintes argumentos opcionais podem ser utilizados para limitar o tamanho
final das imagens:

* Largura máxima: `-mw`
* Altura máxima: `-mh`

O tamanho da imagem será reduzido para o tamanho máximo que caiba dentro da
Largura e/ou altura especificada(s). Se o utilizador introduzir valores para 
ambas as dimensões, serão calculadas as proporções da imagem para cada caso e 
será aplicada a que resulte num tamanho menor.

Tentar otimizar todos os ficheiros de imagem na pasta de trabalho atual, de 
forma recursiva, reduzindo o tamanho de cada imagem para uma larga máxima de 
1600 pixels:

```
optimize-images -mw 1600 ./
```

Tentar otimizar todos os ficheiros de imagem apenas na raiz da pasta de 
trabalho atual, de forma não recursiva, reduzindo o tamanho de cada imagem 
para uma altura máxima de 800 pixels:

```
optimize-images -nr -mh 800 ./
```


#### Monitorizar pasta pela criação de novos ficheiros:

Utilize esta opção quando tiver uma pasta onde pretenda monitorizar o
aparecimento de novos ficheiros de imagem e processá-los logo que possível. A 
aplicação Optimize Images irá vigiar a pasta especificada de forma contínua e
otimizará de forma autmática qualquer ficheiro acabado de criar. Os caminhos dos
ficheiros são guardados numa lista temporária em memória, de modo a que cada 
ficheiro seja processado uma única vez por sessão.

Geralmente, os ficheiros que já existam quando inicia Optimized Images com esta 
opção não serão processados, mas é possível forçar esse processamento. Para tal,
basta usar dois comandos consecutivos: primeiro, uma passagem normal sem o 
argumento `-wd`, para processar os ficheiros existentes; depos, uma segunda 
chamada, desta vez já com o argumento `-wd`, para continuar a vigiar a pasta e
processar quaisquer novos ficheiros à medida que forem criados.

```
optimize-images -wd ./
```

```
optimize-images --watch-directory ./
```

Esta funcionalidade requer o pacote opcional `watchdog`, fornecido por 
terceiros, bem como as suas respetivas dependências, e está disponível apenas 
nos sistemas operativos suportados por ele. Não está disponível, por exemplo, 
em iOS. 

Neste momento, ao utilizar esta funcionalidade, não se encontra disponível a 
execução com multiprocessamento.


#### Número máximo de tarefas em simultâneo

É possível especificar o número máximo de tarefas de processamento a executar em
simultâneo. O valor predefinido (0), na maior parte das plataformas, irá gerar 
um total de N + 1 processos, em que N é o número de processadores ou núcleos 
presentes no sistema.

```
optimize-images -jobs 16 ./
```


### Opções específicas para cada formato:

As seguintes definições específicas para cada formato são opcionais e 
podem ser utilizadas simultaneamente- por exemplo ao processar uma 
pasta que poderá conter imagens em mais do que um formato. As 
definições específicas introduzidas pelo utilizador serão então 
selecionadas e aplicadas automaticamente para cada imagem.

#### JPEG:

##### Qualidade

Defina a qualidade para ficheiros JPEG (um número inteiro, entre 1 e 100), 
usando o argumento `-q`, seguido do valor de qualidade a
aplicar. Um valor mais baixo reduzirá tanto a qualidade de imagem como o
tamanho do ficheiro. A utilização desta opção desativa a definição de
qualidade variável.

Tentar otimizar todos os ficheiros de imagem na pasta de trabalho atual e 
em todas as subpastas, aplicando uma qualidade de 65% aos ficheiros JPEG:

```
optimize-images -q 65 ./
```


##### Manter dados EXIF

Utilize a opção `-ke` ou `--keep-exif` para manter os dados EXIF existentes
em imagens JPEG (por defeito, se não acrescentar este argumento, os dados 
EXIF são apagados.
 
Tentar otimizar todos os ficheiros de imagem na pasta de trabalho atual e
em todas as suas subpastas, aplicando uma qualidade de 65% a ficheiros JPEG
e mantendo os dados EXIF originais:

```
optimize-images -q 65 -ke ./
```


#### PNG:

##### Reduzir o número de cores 

Para reduzir o número de cores (PNG) usando uma paleta de cores adaptativa 
Com difusão, utilize o argumento opcional `-rc`. Esta
opção pode ter um grande impacto no tamanho dos ficheiros, mas por favor
tenha em consideração que também irá afetar de uma forma muito notória a 
qualidade de imagem, especialmente em imagens que tenham gradientes de 
cores e/ou transparência.

Tentar otimizar um único ficheiro de imagem na pasta atual, aplicando uma
paleta de cores adaptativa, com o número de cores predefinido (255):

```
optimize-images -rc ./imagefile.png
```

##### Número máximo de cores

Utilize o argumento opcional `-mc` para especificar o
Número máximo de cores para imagens PNG, ao utilizar a opção de redução de 
cores (um número inteiro entre 0 e 255). O valor predefinido é 255.

Tentar otimizar um único ficheiro de imagem na pasta atual, reduzindo a 
paleta de cores para um valor específico:

```
optimize-images -rc -mc 128 ./imagefile.png
```

Tentar otimizar todos os ficheiros de imagem na pasta atual e em todas as 
suas subpastas, aplicando uma qualidade de 65% aos ficheiros JPEG e 
reduzindo a paleta de cores dos ficheiros PNG para apenas 64 cores:

```
optimize-images -q 60 -rc -mc 64 ./
```

Convém notar que se for indicado um número de cores muito baixo isso pode 
implicar a perda de transparência, substituindo-a por cores inesperadas. Nesses 
casos, é normalmente possível obter melhores resultados utilizando esta opção 
combinada com a remoção explícita de transparência (`rt`) e com a substituição 
da cor de fundo (`-bg` ou `hbg`).

Por exemplo, para otimizar um ficheiro PNG, reduzindo a paleta para o máximo de 
8 cores, removendo a transparência e aplicando um fundo branco:

```
optimize-images -rc -mc 8 -rt -hbg ffffff ./imagefile.png
```


##### Conversão automática de imagens PNG grandes para JPEG

*(trabalho em curso)*

Converter automaticamente para o formato JPEG quaisquer imagens PNG 
grandes que tenham um grande número de cores (presumivelmente uma 
fotografia ou uma imagem semelhante a uma fotografia. Utiliza um 
algoritmo para determinar se será uma boa ideia converter para JPG e 
decide automaticamente sobre isso. Por defeito, ao usar esta opção,
os ficheiros PNG originais permanecerão intactos e serão mantidos 
juntamente com as imagens JPG otimizadas.

**IMPORTANTE: SE JÁ EXISTIR NA MESMA PASTA UM FICHEIRO JPEG COM O 
MESMO NOME, SERÁ SUBSTITUÍDO PELO FICHEIRO JPEG RESULTANTE DESTA
CONVERSÃO.**


```
optimize-images -cb
```

Para forçar o apagamento desses ficheiros PNG originais ao usar a conversão 
automática para JPEG, adicione o argumento `-fd` ou `--force-delete`:

```
optimize-images -cb -fd
```


##### Mudar a cor de fundo predefinida

Por defeito, ao remover a transparência ou ao converter de PNG para
JPEG, será aplicado um fundo branco. É possível escolher uma cor de
fundo diferente usando o argumento `-bg` seguido de 3 números inteiros,
separados por espaços, entre 0 e 255, para Vermelho, Verde e Azul (RGB).
Por exemplo: `255 0 0` (para aplicar um vermelho vivo).

Para converter uma imagem PNG grande com alguma transparência (como, por 
exemplo, capturas de ecrã do macOS) aplicando um fundo preto:

```
optimize-images -cb -bg 0 0 0 ./image.png
```

Se preferir utilizar valores hexadecinais, como os que são usados normalmente
no código HTML, poderá utilizar em alternativa o argumento `-hbg`
seguido do código da cor sem o cardinal (#). Por exemplo:
`00FF00` para uma cor verde pura e viva.

Para converter uma imagem PNG grande com alguma transparência aplicando um 
fundo verde puro:

```
optimize-images -cb -hbg 00FF00 ./image.png
```

### Outras funcionalidades


Consultar o número da versão instalada deste programa:

```
optimize-images -v
```

```
optimize-images --version
```
  
Consultar a lista das extensões usuais dos vários formatos de imagem atualmente 
suportados (note, por favor, que as imagens que não tenham no nome de ficheiro 
a extensão correta correspondente ao seu formato serão ignoradas):

```
optimize-images -s
```

```
optimize-images --supported
```
  
  
## Encontrou um *bug* ou tem uma sugestão?

Por favor avise-nos, abrindo um novo *issue* ou *pull request*.
