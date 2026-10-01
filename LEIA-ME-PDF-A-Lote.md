# PDF/A Lote

Aplicativo portátil para Windows que converte vários PDFs para PDF/A-1b, PDF/A-2b ou PDF/A-3b. O pacote inclui Ghostscript; não é necessário instalar esse motor separadamente.

## Baixar e executar

No GitHub, abra **Actions → Build Windows app**, escolha a execução mais recente concluída e baixe o artefato **PDF-A-Lote-Windows**. Extraia o ZIP inteiro para uma pasta e execute `PDF-A-Lote.exe` de dentro dela. Não mova o executável para fora da pasta extraída, pois ela contém o Ghostscript.

O GitHub Actions gera o pacote Windows automaticamente quando os arquivos do projeto são atualizados na branch `main`. Também é possível iniciar uma compilação manual em **Actions → Build Windows app → Run workflow**. Os artefatos de execução ficam disponíveis por 14 dias.

## Converter e conferir

1. Adicione PDFs ou uma pasta de PDFs.
2. Escolha PDF/A-1b, 2b ou 3b e a pasta de destino.
3. Clique em **Converter lote**.
4. O estado **Convertido; falta validar** significa que Ghostscript concluiu a conversão, mas ainda não houve uma validação de conformidade.
5. Para validar, instale o [veraPDF](https://verapdf.org/software/) separadamente, abra **Validador opcional** e selecione o executável `verapdf` (ou `verapdf.bat`). Se o relatório confirmar conformidade, o status será **PDF/A validado**. Um arquivo reprovado será marcado como falha.

## Limites dos formatos

O Ghostscript gera PDF/A-1b, PDF/A-2b e PDF/A-3b. Ele não gera os níveis A ou U, nem PDF/A-4, 4e ou 4f. Esses perfis não aparecem no seletor porque exigem outro motor de conversão compatível. O veraPDF é validador, não conversor.

A validação independente é importante: terminar a conversão não garante que o arquivo resultante esteja conforme. Os PDFs de origem permanecem intactos; saídas com nomes repetidos são preservadas, salvo se a opção de substituição estiver marcada.

## Licenças

Este aplicativo é distribuído sob AGPL-3.0; consulte `LICENSE`. O pacote inclui Ghostscript, software AGPL da Artifex; consulte `TERCEIROS.md` e mantenha os avisos junto ao programa. O código-fonte correspondente desta versão está em [github.com/iuremaciel/converter](https://github.com/iuremaciel/converter). A distribuição deste pacote exige que os termos AGPL sejam respeitados.

## Referências

- [Ghostscript: criação de PDF/A](https://ghostscript.readthedocs.io/en/latest/VectorDevices.html#creating-a-pdf-a-document)
- [veraPDF: validação pela linha de comando](https://docs.verapdf.org/cli/validation/)
- [PyInstaller](https://pyinstaller.org/en/stable/)
