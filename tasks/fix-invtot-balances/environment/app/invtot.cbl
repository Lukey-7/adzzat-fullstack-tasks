      * INVTOT - invoice balances per customer.
      *
      * Reads invoice records from standard input, one per line, in
      * fixed columns:
      *   cols  1-6   customer id (any characters). Records of one
      *               customer are adjacent.
      *   col   7     C = charge, R = refund
      *   cols  8-10  quantity, 3 digits (000-999)
      *   cols 11-17  unit price in cents, 7 digits (0000000-9999999)
      * A record's amount is quantity x unit price plus 7.5% tax,
      * rounded half up to the cent. Charges add to the customer's
      * balance and refunds subtract from it, so a balance can be
      * negative. Balances stay within +/-999,999,999.99.
      *
      * Any other line (wrong type letter, a quantity or price that is
      * not all digits, a short or blank line) is rejected: it is
      * skipped and counted.
      *
      * Output: one line per customer with at least one accepted
      * record, in input order, then a grand total and the reject
      * count:
      *   CCCCCC +999999999.99
      *   TOTAL  +99999999999.99
      *   REJECTED 99999
      * (sign, zero-padded digits, decimal point, two decimals).
      *
      * Copyright (c) 2026 Varun R Darji. MIT licence, see LICENSE.
      *
       IDENTIFICATION DIVISION.
       PROGRAM-ID. INVTOT.
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT INVOICES ASSIGN TO KEYBOARD
               ORGANIZATION IS LINE SEQUENTIAL.
       DATA DIVISION.
       FILE SECTION.
       FD  INVOICES.
       01  INV-REC.
           05  INV-CUST            PIC X(6).
           05  INV-TYPE            PIC X.
           05  INV-QTY             PIC X(3).
           05  INV-QTY-N REDEFINES INV-QTY
                                   PIC 9(3).
           05  INV-PRICE           PIC X(7).
           05  INV-PRICE-N REDEFINES INV-PRICE
                                   PIC 9(5)V99.
       WORKING-STORAGE SECTION.
       01  WS-EOF                  PIC X VALUE 'N'.
       01  WS-FIRST                PIC X VALUE 'Y'.
       01  WS-CUR-CUST             PIC X(6).
       01  WS-LINE                 PIC 9(9)V99.
       01  WS-CUST-TOTAL           PIC 9(7)V99.
       01  WS-GRAND                PIC S9(11)V99 VALUE 0.
       01  WS-REJECTED             PIC 9(5) VALUE 0.
       01  OUT-CUST.
           05  OUT-ID              PIC X(6).
           05  FILLER              PIC X VALUE SPACE.
           05  OUT-AMT             PIC +9(9).99.
       01  OUT-TOTAL.
           05  FILLER              PIC X(7) VALUE 'TOTAL  '.
           05  OUT-GRAND           PIC +9(11).99.
       01  OUT-REJ.
           05  FILLER              PIC X(9) VALUE 'REJECTED '.
           05  OUT-REJ-N           PIC 9(5).
       PROCEDURE DIVISION.
       MAIN-PARA.
           OPEN INPUT INVOICES
           PERFORM UNTIL WS-EOF = 'Y'
               READ INVOICES
                   AT END MOVE 'Y' TO WS-EOF
                   NOT AT END PERFORM PROCESS-REC
               END-READ
           END-PERFORM
           IF WS-FIRST = 'N'
               PERFORM PRINT-CUST
           END-IF
           MOVE WS-GRAND TO OUT-GRAND
           DISPLAY OUT-TOTAL
           MOVE WS-REJECTED TO OUT-REJ-N
           DISPLAY OUT-REJ
           CLOSE INVOICES
           STOP RUN.
       PROCESS-REC.
           IF (INV-TYPE NOT = 'C' AND INV-TYPE NOT = 'R')
              OR INV-QTY IS NOT NUMERIC
              OR INV-PRICE IS NOT NUMERIC
               ADD 1 TO WS-REJECTED
           ELSE
               IF WS-FIRST = 'Y'
                   MOVE 'N' TO WS-FIRST
                   MOVE INV-CUST TO WS-CUR-CUST
                   MOVE 0 TO WS-CUST-TOTAL
               ELSE
                   IF INV-CUST NOT = WS-CUR-CUST
                       PERFORM PRINT-CUST
                       MOVE INV-CUST TO WS-CUR-CUST
                       MOVE 0 TO WS-CUST-TOTAL
                   END-IF
               END-IF
               COMPUTE WS-LINE =
                   INV-QTY-N * INV-PRICE-N * 1.075
               IF INV-TYPE = 'C'
                   ADD WS-LINE TO WS-CUST-TOTAL WS-GRAND
               ELSE
                   SUBTRACT WS-LINE FROM WS-CUST-TOTAL WS-GRAND
               END-IF
           END-IF.
       PRINT-CUST.
           MOVE WS-CUR-CUST TO OUT-ID
           MOVE WS-CUST-TOTAL TO OUT-AMT
           DISPLAY OUT-CUST.
