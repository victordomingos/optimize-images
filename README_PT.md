[English](https://github.com/victordomingos/optimize-images/blob/master/README.md) | **[Portugu&ecirc;s](https://github.com/victordomingos/optimize-images/blob/master/docs/README_PT.md)**


# Optimize Images [![Github commits (since latest release)](https://img.shields.io/github/commits-since/victordomingos/optimize-images/latest.svg)](https://github.com/victordomingos/optimize-images)
Um utilitário de linha de comandos escrito um Python para ajudar a reduzir o
tamanho de ficheiros de imagens.

Esta aplicação é escrita tanto quanto possível em Python puro, sem requisitos
técnicos especiais para além do Pillow, assegurando deste modo a
compatibilidade com um vasto leque de sistemas, incluindo iPhones e iPads com
a app Pythonista 3. Caso não tenha a necessidade de uma gestão de dependências
tão rigorosa, encontrará certamente várias outras ferramentas de otimização de
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

A atual versão de desenvolvimento pode ser instalada com o comando
`pip install -e`, seguido do caminho para a pasta principal do projeto (a
mesma pasta que contém o ficheiro `setup.py`). Para executar esta aplicação é
necessária uma instalação do Python 3.6 ou superior. Procuramos manter no
mínimo as dependências externas, de modo a manter a compatibilidade com
diferentes plataformas, incluindo Pythonista em iOS. Neste momento, requer:

  - Pillow==5.1.0
  - piexif==1.0.13

Nota: Se está a utilizar um Mac com Python 3.6 e macOS X 10.11 El Capitan ou
anterior, deverá usar antes a versão Pillow 5.0.0. No caso de já ter migrado 
para Python3.7, não deverá ter problemas com o Pillow 5.1.0.

Planeamos submeter esta aplicação ao PyPI tão brevemente quanto possível, para
permitir oferecer uma forma de instalação e atualização mais simples.
Enquanto isso não acontece, estejam à vontade para dar uma olhada na última
secção e talvez considerar contribuir também para este projeto.



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
selfupdate.py -f bennr01:command_testing
```

De seguida, force o encerramento do Pythonista, reiniciando-o de seguida, e
inicie novamente a StaSh. Deverá estar agora a correr em Python 3. Neste
momento, pode tentar instalar esta aplicação, diretamente a partir deste
repositório:

```
pip install victordomingos/optimize-images
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


## Como utilizar

A forma mais simples de utilização consiste na introdução de um comando simples 
na linha de comandos, passando o caminho para uma imagem ou uma pasta contendo 
imagens como argumento.

Os argumentos opcionais `-nr` ou `--no-recursion` dizem à aplicação para não
percorrer de forma recursiva todas as subpastas (ou seja, processar imagens 
apenas na raiz da pasta indicada).

Por defeito, esta ferramenta aplica compressão com perdas a ficheiros JPEG 
utilizando um valor de qualidade de 80% (pela escala do Pillow), remove 
quaisquer metadados EXIF existentes, tenta otimizar as definições de cada 
encodificador para a máxima redução de espaço e aplica a compressão ZLIB 
máxima em ficheiros PNG.

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
adaptativa. Tenha em consideração que ao usar esta opção todas as imagens PNG 
irão perder a transparência e a qualidade de imagem poderá ser afetada de 
forma bastante notória.

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

#### Redimensionamento de imagens:

These options will be applied individually to each image being processed. Any 
image that has a dimension exceeding a specified value will be downsized as 
the first optimization step. The resizing will not take effect if, after the 
whole optimization process, the resulting file size isn't any smaller than 
the original. These options are disabled by default.

These optional arguments can be used to constrain the final size of the images:

* Maximum width: `-mw` or `--max-width` 
* Maximum height: `-mh` ou `--max-height`

The image will be downsized to a maximum size that fits the specified 
width and/or height. If the user enters values to both dimensions, it will 
calculate the image proportions for each case and use the one that results in 
a smaller size. 

Try to optimize all image files in current working directory, with recursion, 
downsizing each of them to a maximum width of 1600 pixels:

```
optimize-images -mw 1600 ./
```

```
optimize-images --max-width 1600 ./
```


Try to optimize all image files in current working directory, without 
recursion, downsizing each of them to a maximum height of 800 pixels:

```
optimize-images -nr -mh 1600 ./
```

```
optimize-images --no-recursion --max-height 800 ./
```



### Opções específicas para cada formato:

The following format specific settings are optional and may be used
simultaneously, for instance when processing a directory that may
contain images in more than one format. The appropriate format-specific
options entered by the user will then be automatically selected and
applied for each image.

#### JPEG:

##### Qualidade

Set the quality for JPEG files (an integer value, between 1 and 100), using 
the `-q` or `--quality` argument, folowed by the quality value to apply.
A lower value will reduce both the image quality and the file size. The
default value is 80.

Try to optimize all image files in current working directory and all of its
subdirectories, applying a quality of 65% to JPEG files:

```
optimize-images -q 65 ./
```

```
optimize-images --quality 65 ./
```
  

##### Manter dados EXIF

Use the `-ke` or `--keep-exif`) to keep existing image EXIF data in JPEG 
images (by default, if you don't add this argument, EXIF data is discarded).

Try to optimize all image files in current working directory and all of its
subdirectories, applying a quality of 65% to JPEG files and keeping the 
original EXIF data:

```
optimize-images -q 65 -ke ./
```

```
optimize-images --quality 65 --keep-exif ./
```


#### PNG:

##### Reduzir o número de cores 

To reduce the number of colors (PNG) using an adaptive color palette with 
dithering, use the `-rc` or `--reduce-colors` optional argument.
This option can have a big impact on file size, but please note that
will also affect image quality in a very noticeable way, especially in
images that have color gradients and/or transparency.

Try to optimize a single image file in current working directory,
applying and adaptive color palette with the default amount of colors
(255):

```
optimize-images -rc ./imagefile.png
```
```
optimize-images --reduce-colors ./imagefile.png
```


##### Número máximo de cores

Use the  `-mc` or `--max-colors` optional argument to specify the maximum  
number of colors for PNG images when using the reduce colors (-rc) option 
(an integer value, between 0 and 255). The default value is 255.

Try to optimize a single image file in current working directory,
reducing the color palette to a specific value:

```
optimize-images -rc -mc 128 ./imagefile.png
```
```
optimize-images --reduce-colors --max-colors 128 ./imagefile.png
```

Try to optimize all image files in current working directory and all of
its subdirectories, applying a quality of 65% to JPEG files and
reducing the color palette of PNG files to just 64 colors:

```
optimize-images -q 60 -rc -mc 64 ./
```
```
optimize-images --quality 60 --reduce-colors --max-colors 64 ./
```


##### Conversão automática de imagens PNG grandes para JPEG

*(work in progess)*

Automatically convert to JPEG format any big PNG images that have with a
large number of colors (presumably a photo or photo-like image). It uses
an algorithm to determine whether it is a good idea to convert to JPG
and automatically decide about it. By default, when using this option,
the original PNG files will remain untouched and will be kept alongside
the optimized JPG images in their original folders.

IMPORTANT: IF A JPEG WITH THE SAME NAME ALREADY EXISTS, IT WILL BE
REPLACED BY THE JPEG FILE RESULTING FROM THIS CONVERTION.**


```
optimize-images -cc
```

```
optimize-images --convert_big
```


You may force the deletion of the original PNG files when using
automatic convertion to JPEG, by adding the `-fd` or `--force-delete`
argument:

```
optimize-images -cc -fd
```

```
optimize-images --convert_big --force-delete
```


##### Mudar a cor de fundo predefinida

By default, when you choose some operations that remove transparency,
like reducing colors or converting from PNG to JPEG it will apply a
white background color. You may choose a different background by using
the argument `-bg` or `--background-color` folowed by 3 integer numbers,
separated by spaces, between 0 and 255, for Red, Green and Blue. E.g.:
`255 0 0` for a pure red color).


To convert a big PNG image with some transparency (like, for instance,
macOS screenshots) applying a black background:
```
optimize-images -cc -bg 0 0 0 ./image.png
```

```
optimize-images --convert_big --bg-color 0 0 0 ./image.png
```

If you prefer to use hexadecimal values, like those that are usual in
HTML code, you may alternatively use the argument `-hbg` or
`--hex-bg-color` folowed by the color code without the hash (#)
character. E.g.: `00FF00` for a pure
green color).

To convert a big PNG image with some transparency applying a pure green
background:

```
optimize-images -cc -hbg 0 255 0 ./image.png
```

```
optimize-images --convert_big --hex-bg-color 00FF00 ./image.png
```

### Other features


Check the installed version of this application:

```
optimize-images -v
```

```
optimize-images --version
```
  

View a list of the supported image formats by their usual filename extensions 
(please note that files without the corresponding file extension will be ignored):

```
optimize-images -sf
```

```
optimize-images --supported-formats
```
  
  
## Encontrou um *bug* ou tem uma sugestão?

Por favor avise-nos, abrindo um novo *issue* ou *pull request*.
