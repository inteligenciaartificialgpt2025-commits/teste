# Automação de cliques e teclas em janelas do Windows

Aplicativo Python com interface gráfica em Tkinter para configurar rotinas de teclas, combinações de teclas e cliques relativos a uma janela específica do Windows.

## Instalação para usuário final

O usuário comum deve instalar apenas pelo instalador gerado pelo Inno Setup. Ele não precisa abrir terminal, instalar Python ou instalar bibliotecas manualmente.

1. Execute `AutomacaoJanelasSetup-1.0.0.exe`.
2. Siga o assistente de instalação.
3. O programa será instalado em `C:\Program Files\Automacao Janelas`.
4. O instalador cria atalho no Menu Iniciar e, por padrão, na Área de Trabalho.
5. Para remover, use **Configurações > Aplicativos** ou **Painel de Controle > Programas e Recursos**.

## Como usar o aplicativo

1. Clique em **Atualizar janelas** e escolha a janela alvo.
2. Cadastre uma ou mais ações:
   - **tecla**: exemplos `f1`, `enter`, `esc`.
   - **combinação**: exemplos `ctrl+c`, `ctrl+v`, `alt+tab`.
   - **clique**: coordenadas `x,y` relativas ao canto superior esquerdo da janela escolhida.
3. Defina intervalo em segundos, repetições e ordem.
4. Use **Iniciar**, **Pausar/Continuar**, **Parar** ou **EMERGÊNCIA**.
5. Salve/carregue rotinas em JSON pelos botões da interface.

Os arquivos JSON são salvos/carregados inicialmente em `%APPDATA%\Automacao Janelas`, uma pasta gravável do usuário. Isso evita tentar gravar configurações dentro de `Program Files`.

## Gerar o executável com PyInstaller

> Esta etapa é feita apenas na máquina de build/desenvolvimento. O usuário final não precisa ter Python.

Pré-requisitos na máquina de build:

- Windows 64 bits.
- Python 3.10+ instalado.
- Acesso à internet para instalar dependências.

Passos:

1. Abra o Explorer na pasta do projeto.
2. Dê dois cliques em `build_exe.bat`.
3. O script cria `.venv`, instala `requirements.txt`, instala `pyinstaller` e gera o pacote do aplicativo.
4. O executável será criado em:

```text
dist\AutomacaoJanelas\AutomacaoJanelas.exe
```

Se existir um ícone em `assets\app.ico`, ele será usado no executável. Se não existir, o ícone padrão do PyInstaller será usado.

## Instalar o Inno Setup

1. Baixe o Inno Setup em <https://jrsoftware.org/isinfo.php>.
2. Instale a versão mais recente no Windows.
3. Após instalar, abra o arquivo `installer.iss` com o **Inno Setup Compiler**.

## Gerar o instalador final

1. Execute `build_exe.bat` e confirme que `dist\AutomacaoJanelas\AutomacaoJanelas.exe` foi criado.
2. Abra `installer.iss` no Inno Setup Compiler.
3. Clique em **Compile**.
4. O instalador final será gerado em:

```text
installer\AutomacaoJanelasSetup-1.0.0.exe
```

O instalador copia os arquivos de `dist\AutomacaoJanelas` para `C:\Program Files\Automacao Janelas`, cria atalhos e registra o desinstalador no Windows.

## Como testar a instalação

1. Execute `installer\AutomacaoJanelasSetup-1.0.0.exe`.
2. Mantenha a opção de atalho na Área de Trabalho marcada.
3. Finalize a instalação e abra o programa pelo Menu Iniciar ou pelo atalho da Área de Trabalho.
4. Clique em **Atualizar janelas** para confirmar que as janelas abertas aparecem.
5. Crie uma rotina simples, por exemplo uma ação `tecla` com valor `f1` e uma repetição.
6. Salve a rotina em JSON e confirme que o diálogo abre em `%APPDATA%\Automacao Janelas`.
7. Desinstale pelo Painel de Controle ou Configurações do Windows e confirme que o aplicativo foi removido.

## Segurança

Antes de cada ação, o programa verifica se a janela alvo ainda existe, restaura/ativa somente essa janela e valida cliques para impedir coordenadas fora dos limites da janela. A execução roda em thread separada para manter a interface responsiva.
