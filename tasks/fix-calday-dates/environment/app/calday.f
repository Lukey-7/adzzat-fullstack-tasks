C     CALDAY - a small calendar calculator for Gregorian dates.
C
C     Reads queries from standard input, one per line, and writes one
C     answer line per query:
C
C       DIFF Y1 M1 D1 Y2 M2 D2   days from the first date to the second
C                                (negative if the second is earlier)
C       ADD  Y M D N             the date N days after Y-M-D (N may be
C                                negative), written as YYYY-MM-DD
C       DOW  Y M D               day of the week, e.g. MONDAY
C
C     Years must be in 1601..3000. Any invalid query, invalid date or
C     out-of-range result gives the answer line ERROR. Blank lines are
C     skipped.
C
C     Day numbers use the Julian Day Number formulas of Fliegel and
C     Van Flandern, Comm. ACM 11(10):657 (1968).
C
C     Copyright (c) 2026 Varun R Darji. MIT licence, see LICENSE.
C
      PROGRAM CALDAY
      INTEGER Y1, M1, D1, Y2, M2, D2, N, J, K, IOS
      INTEGER JDN
      LOGICAL VALID
      CHARACTER*200 LINE
      CHARACTER*9 DNAME(0:6)
      DATA DNAME /'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY',
     &            'FRIDAY', 'SATURDAY', 'SUNDAY'/
C
   10 READ (*, '(A)', IOSTAT=IOS) LINE
      IF (IOS .NE. 0) STOP
      IF (LINE .EQ. ' ') GO TO 10
      LINE = ADJUSTL(LINE)
C
      IF (LINE(1:5) .EQ. 'DIFF ') THEN
         READ (LINE(6:), *, IOSTAT=IOS) Y1, M1, D1, Y2, M2, D2
         IF (IOS .NE. 0) GO TO 90
         IF (.NOT. VALID(Y1, M1, D1)) GO TO 90
         IF (.NOT. VALID(Y2, M2, D2)) GO TO 90
         WRITE (*, '(I0)') JDN(Y2, M2, D2) - JDN(Y1, M1, D1)
C
      ELSE IF (LINE(1:4) .EQ. 'ADD ') THEN
         READ (LINE(5:), *, IOSTAT=IOS) Y1, M1, D1, N
         IF (IOS .NE. 0) GO TO 90
         IF (.NOT. VALID(Y1, M1, D1)) GO TO 90
         J = JDN(Y1, M1, D1) + N
         CALL GREG(J, Y2, M2, D2)
         IF (.NOT. VALID(Y2, M2, D2)) GO TO 90
         WRITE (*, '(I4.4, A, I2.2, A, I2.2)') Y2, '-', M2, '-', D2
C
      ELSE IF (LINE(1:4) .EQ. 'DOW ') THEN
         READ (LINE(5:), *, IOSTAT=IOS) Y1, M1, D1
         IF (IOS .NE. 0) GO TO 90
         IF (.NOT. VALID(Y1, M1, D1)) GO TO 90
C        Julian Day Number 0 fell on a Monday.
         K = MOD(JDN(Y1, M1, D1), 7)
         WRITE (*, '(A)') TRIM(DNAME(K))
C
      ELSE
         GO TO 90
      END IF
      GO TO 10
C
   90 WRITE (*, '(A)') 'ERROR'
      GO TO 10
      END
C
C     ------------------------------------------------------------------
C     Julian Day Number of the Gregorian date Y-M-D.
C
      INTEGER FUNCTION JDN(Y, M, D)
      INTEGER Y, M, D, A
      A = (M - 14) / 12
      JDN = D - 32075 + 1461*(Y + 4800 + A)/4 + 367*(M - 2 - A*12) / 12 - 3*((Y + 4900 + A)/100)/4
      END
C
C     ------------------------------------------------------------------
C     Inverse of JDN: the Gregorian date Y-M-D of Julian Day Number J.
C
      SUBROUTINE GREG(J, Y, M, D)
      INTEGER J, Y, M, D, L, N, I, K
      L = J + 68569
      N = 4 * L / 146097
      L = L - (146097 * N + 3) / 4
      I = 4000 * (L + 1) / 1461001
      L = L - 1461 * I / 4 + 31
      K = 80 * L / 2447
      D = L - 2447 * K / 80
      L = K / 11
      M = K + 2 - 12 * L
      Y = 100 * (N - 49) + I + L
      END
C
C     ------------------------------------------------------------------
C     .TRUE. if Y-M-D is a real Gregorian date with Y in 1601..3000.
C
      LOGICAL FUNCTION VALID(Y, M, D)
      INTEGER Y, M, D, DIM(12)
      LOGICAL LEAP
      DATA DIM /31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31/
      VALID = .FALSE.
      IF (Y .LT. 1601 .OR. Y .GT. 3000) RETURN
      IF (M .LT. 1 .OR. M .GT. 12) RETURN
      LEAP = MOD(Y, 4) .EQ. 0 .AND.
     &       (MOD(Y, 100) .NE. 0 .OR. MOD(Y, 400) .EQ. 0)
      IF (D .LT. 1) RETURN
      IF (M .EQ. 2 .AND. LEAP) THEN
         IF (D .GT. 29) RETURN
      ELSE
         IF (D .GT. DIM(M)) RETURN
      END IF
      VALID = .TRUE.
      END
