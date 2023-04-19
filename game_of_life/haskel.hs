--- Normal comment
{- 
Comment
spanning
multiple
lines 
-}

-- open prompt with "ghci"
-- open file with ":l file.hs"
-- run file with ":r"

import Data.List
import System.IO

-- Int, between -2^63 and 2^63 
minInt = minBound :: Int
maxInt = maxBound :: Int
always5 :: Int
always5 = 5 

-- Integer, unbounded whole number (depending on size of memory)
-- Float
-- Double
-- Bool True or False
-- Char ''
-- Tuple

sum_of_nums = sum [1..1000]
add_ex = 5 + 4
sub_ex = 5 - 4
mult_ex = 5 * 4
div_ex = 5 / 4

mod_ex = mod 5 4 -- prefix operator
mod_ex2 = 5 `mod` 4 -- infix operator

neg_num_ex = 5 + (-4) -- negative numbers have to be escaped with parentheses

-- get help about a function with ":t sqrt"
-- output "sqrt :: Floating a => a -> a"

num9 = 9 :: Int
sqrt_of_9 = sqrt (fromIntegral num9) -- convert to float first

-- other built-in math functions:
-- pi, exp v, log v, x ** y, truncate, round, ceiling, floor
-- sin, cos, tan, asin, acos, atan, sinh, cosh, tanh, asinh, acosh, atanh 

-- for booleans:
true_and_false = True && False
true_or_false = True || False
not_true = not(True)

prime_numbers = [3,5,7,11]
more_primes = prime_numbers ++ [13,17,19,23,29]
even_more_primes = 2 : more_primes

len_prime = length even_more_primes
reverse_primes = reverse even_more_primes 

is_list_empty = null even_more_primes -- check if the list is empty
is_7_in_list = 7 `elem` even_more_primes -- check if 7 is in the list
max_prime = maximum even_more_primes
min_prime = minimum even_more_primes

first_prime = head even_more_primes
second_prime = even_more_primes !! 1
last_prime = last even_more_primes
prime_init = init even_more_primes -- will return everything BUT the last value
first_3_primes = take 3 even_more_primes -- returns the first three values
primes_removed = drop 3 even_more_primes -- returns everything BUT the first three values

some_numbers = 2 : 7 : 21 : 66 :[] -- [] denotes the end of the list
multi_list = [[3,5,7],[11,13,17]]
some_value = multi_list !! 1 !! 2
two_to_five = [2..5]
product_of_list = product two_to_five
even_list = [2,4..10]



