# invtot

A small invoice-balance program in fixed-format COBOL (GnuCOBOL), written for
this exercise (MIT, see `../LICENSE`). It reads fixed-column invoice records
on standard input and prints one balance per customer, a grand total and a
count of rejected lines. The specification is the comment block at the top of
`invtot.cbl`.

    cobc -x -o invtot invtot.cbl
    ./invtot < ../tasks/fix-invtot-balances/environment/app/examples/invoices.txt

This is the correct version. Task `fix-invtot-balances` ships it with three
defects in its data definitions.
