module Metonymy.GF
  ( linearize
  , parseEnglish
  , spaceBeforeCommas
  , spaceAroundParens
  ) where

import Data.Char (isSpace)
import System.Exit (ExitCode (..))
import System.Process (readProcessWithExitCode)

linearize :: FilePath -> String -> IO (Either String String)
linearize pgfPath expression = do
  (exitCode, stdoutText, stderrText) <-
    readProcessWithExitCode
      "gf"
      ["--run", pgfPath]
      ("l -lang=GeneratedMetonymyEng " <> expression <> "\n")
  pure $
    case exitCode of
      ExitSuccess -> Right (trim stdoutText)
      ExitFailure _ -> Left (trim stderrText)

parseEnglish :: FilePath -> String -> IO (Either String [String])
parseEnglish pgfPath sentence = do
  (exitCode, stdoutText, stderrText) <-
    readProcessWithExitCode
      "gf"
      ["--run", pgfPath]
      ( "p -lang=GeneratedMetonymyEng \""
          <> spaceAroundParens (spaceBeforeCommas sentence)
          <> "\"\n"
      )
  pure $
    case exitCode of
      ExitSuccess -> Right (filter (not . null) (map trim (lines stdoutText)))
      ExitFailure _ -> Left (trim stderrText)

-- GF's parser uses a whitespace-only tokenizer by default: a comma with
-- no preceding space ("programme,") is one indivisible token, not two,
-- and no grammar-level device (BIND/SOFT_BIND included -- confirmed by
-- direct local testing against a real gf.exe build, not guessed) can
-- retroactively split an already-fused input token at parse time. Every
-- comma-using grammar construct (BecauseS/SBecauseS-family,
-- ApposCommaPN1/ApposCommaPN2 in grammar/MetonymyEng.gf) needs its
-- comma to arrive as its own token, exactly like natural English commas
-- already are once a space precedes them. This inserts that space only
-- when one isn't already there, so it's a no-op for every sentence that
-- doesn't reach a comma-using construct -- which, before this session's
-- comma-based grammar additions, was every sentence this engine ever
-- parsed.
spaceBeforeCommas :: String -> String
spaceBeforeCommas (a : b : rest)
  | b == ',' && a /= ' ' = a : ' ' : b : spaceBeforeCommas rest
  | otherwise = a : spaceBeforeCommas (b : rest)
spaceBeforeCommas other = other

-- Same tokenizer limitation, same fix, for parentheses: "Foundation
-- (HOLA)" needs "(" and ")" as their own tokens for grammar/Metonymy.gf's
-- ParenNP to ever be reachable -- confirmed directly (not guessed) by
-- testing against a locally compiled grammar: with no spacing,
-- "(HOLA)" is one indivisible token that an unrelated existing
-- multi-word-proper-noun rule (OpenPN3) silently absorbed instead,
-- producing a real but semantically wrong tree, the exact same failure
-- shape ApposCommaPN1/ApposCommaPN2 had before spaceBeforeCommas. Only
-- touches "(" and ")" specifically, inserting a space on the side that
-- would otherwise glue to an adjacent non-space character.
spaceAroundParens :: String -> String
spaceAroundParens (a : b : rest)
  | a /= ' ' && b == '(' = a : ' ' : spaceAroundParens (b : rest)
  | a == ')' && b /= ' ' = a : ' ' : spaceAroundParens (b : rest)
  | otherwise = a : spaceAroundParens (b : rest)
spaceAroundParens other = other

trim :: String -> String
trim = dropWhileEnd isSpace . dropWhile isSpace
  where
    dropWhileEnd predicate = reverse . dropWhile predicate . reverse
