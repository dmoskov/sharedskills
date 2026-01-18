input number = n
0 = steps
n 1 = greater
{ greater 0 >
  n 2 % 0 == { n 2 / = n } { n 3 * 1 + = n } ternary
  steps 1 + = steps
  n 1 > = greater
} 
loop
steps output
