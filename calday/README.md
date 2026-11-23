# calday

A small calendar calculator in fixed-form Fortran 77, written for this
exercise (MIT, see `../LICENSE`). It answers `DIFF`, `ADD` and `DOW` queries
about Gregorian dates in 1601..3000. The specification is the comment block
at the top of `calday.f`. Day numbers use the Julian Day Number formulas of
Fliegel and Van Flandern, *Comm. ACM* 11(10):657 (1968).

    gfortran -o calday calday.f
    printf 'DIFF 2024 1 1 2024 3 1\nADD 2024 2 28 2\nDOW 2024 1 1\n' | ./calday

This is the correct version. Task `fix-calday-dates` ships it with one
regression; task `count-workdays` ships it unchanged as code the agent may
reuse.
