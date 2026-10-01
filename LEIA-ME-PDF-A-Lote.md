# PDF/A Lote

Aplicativo desktop para Windows que organiza conversões PDF/A em lote, mantém os originais intactos e mostra o estado de cada arquivo. Para executar a versão fonte, inicie `pdfa_lote.py` com Python 3 instalado.

## Gerar o executável pelo GitHub

O repositório precisa conter os arquivos desta pasta na raiz: `pdfa_lote.py` e `.github/workflows/build-windows.yml`. Envie-os para um repositório GitHub na branch `main`. O workflow compila o app para Windows quando esse arquivo é enviado à branch, ou manualmente em **Actions → Build Windows app → Run workflow**. Ao terminar, baixe `PDF-A-Lote-Windows` na seção **Artifacts** da execução. O artefato contém `PDF-A-Lote.exe`.

O `.exe` empacota o Python e a interface, mas não inclui Ghostscript, veraPDF nem um conversor PDF/A comercial. Instale e configure esses motores à parte no computador onde o app será usado.

## Perfis

O seletor apresenta os 11 formatos pedidos: PDF/A-1b, 1a, 2b, 2u, 2a, 3b, 3u, 3a, 4, 4e e 4f. Para converter todos eles, configure em **Configurar motor** um conversor de linha de comando que aceite o perfil escolhido. Os argumentos padrão são:

```text
--profile {profile} --input {input} --output {output}
```

Edite os argumentos para corresponder ao conversor instalado. `{profile}` recebe, por exemplo, `2u`; `{input}` e `{output}` recebem os caminhos dos arquivos. O conversor e o validador rodam localmente.

## Opção gratuita parcial

O Ghostscript integrado pode processar PDF/A-1b, 2b e 3b. Ele precisa estar instalado, junto com o arquivo `PDFA_def.ps` configurado com um perfil ICC válido. Instale também o veraPDF para validar o resultado. Os demais perfis não são convertidos pelo Ghostscript.

O veraPDF valida todos os perfis listados, mas não converte PDFs. Se ele estiver configurado, o app só marcará um arquivo como **PDF/A validado** quando o relatório XML do veraPDF confirmar conformidade. Sem validador, o estado fica como **Convertido; falta validar**.

## Observações

- PDFs de origem não são alterados; os resultados vão para a pasta escolhida (ou para uma subpasta `PDF-A` junto aos originais).
- Arquivos com o mesmo nome de saída são preservados, a menos que “Substituir arquivos existentes” esteja marcado.
- A criação de um PDF/A-1a, 2a, 2u, 3a, 3u, 4, 4e ou 4f depende de um conversor compatível. O programa não promete que apenas adicionar metadados torne o arquivo conforme.
- Esta é uma primeira versão funcional da interface. Para distribuir como instalador `.exe`, ainda é necessário empacotar o Python e decidir como distribuir/licenciar o motor completo.

## Referências técnicas

- [Ghostscript: criação PDF/A](https://ghostscript.readthedocs.io/en/latest/VectorDevices.html#creating-a-pdf-a-document) — documenta criação apenas para PDF/A-1, -2 e -3 no nível b.
- [veraPDF: validação pela linha de comando](https://docs.verapdf.org/cli/validation/) — lista os perfis de validação 1a/1b, 2a/2b/2u, 3a/3b/3u, 4/4e/4f.
- [PyInstaller: modo de arquivo único e janela sem console](https://pyinstaller.org/en/stable/usage.html) — opções usadas pelo workflow para gerar o `.exe` Windows.
- [GitHub Actions: artefatos de workflow](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts) — explica como baixar o `.exe` enviado pelo build.
