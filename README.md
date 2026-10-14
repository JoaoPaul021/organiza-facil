# Organiza Fácil

Aplicativo desktop gratuito para organizar os arquivos de uma pasta por tipo.

## O que ele faz

- Analisa apenas os arquivos diretamente dentro da pasta escolhida.
- Mostra uma pré-visualização antes de mover qualquer item.
- Organiza arquivos em pastas como Imagens, Documentos, Videos, Audios e Codigo.
- Não sobrescreve arquivos existentes: cria nomes como `arquivo (1).pdf`.
- Permite desfazer a última organização durante a mesma execução.
- Funciona localmente e não envia arquivos para a internet.

## Como executar

1. Instale o Python 3 no computador, caso ainda não esteja instalado.
2. Abra `executar_organiza_facil.bat` ou execute `python organiza_facil.py`.
3. Escolha uma pasta.
4. Clique em `Pré-visualizar`.
5. Clique em `Organizar agora` somente depois de conferir a lista.

## Versão para distribuir

O arquivo `.github/workflows/build-windows.yml` faz o GitHub Actions gerar uma versão `OrganizaFacil.exe` para Windows. Ele é executado na aba `Actions` do repositório e entrega um arquivo para download em `Artifacts`.

Para distribuição pública, publique o `.exe` ou o `.zip` em uma Release do GitHub. A primeira versão não precisa de Stripe, PayPal ou servidor próprio, porque será gratuita.

## Limitações atuais

- Não percorre subpastas.
- A opção de desfazer vale apenas para a última organização feita naquela execução.
- A classificação é baseada na extensão do arquivo.

## Próximas versões possíveis

- Escolha das categorias pelo usuário.
- Histórico salvo para permitir desfazer depois de fechar o aplicativo.
- Modo automático para a pasta Downloads.
- Filtros por data e tamanho.
- Empacotamento em um arquivo executável para Windows.
