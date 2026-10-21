# SPDX-FileCopyrightText: 2026 Sebastien Rousseau <sebastian.rousseau@gmail.com>
# SPDX-License-Identifier: Apache-2.0 OR MIT
#
# Rendered by `make demo` (vhs, https://github.com/charmbracelet/vhs) from
# the repository root, against the AC04 statement the tests use. Nothing
# here reaches the network.
Output .github/demo.gif

Set Shell "bash"
Set FontSize 14
Set Width 1200
Set Height 640
Set Padding 20
Set Theme "Catppuccin Mocha"

Hide
Type "export PS1='$ ' && clear"
Enter
Show

Type "camt053 entries -i tests/gold_master/statement_ac04.xml"
Sleep 500ms
Enter
Sleep 2s

Type "camt053 entries -i tests/gold_master/statement_ac04.xml -r AC04"
Sleep 500ms
Enter
Sleep 2s

Type "camt053 reverse -i tests/gold_master/statement_ac04.xml -r AC04 -o reversal.xml"
Sleep 500ms
Enter
Sleep 2s

Type "camt053 validate -i reversal.xml && camt053 entries -i reversal.xml"
Sleep 500ms
Enter
Sleep 4s

Hide
Type "rm -f reversal.xml"
Enter
Sleep 500ms
