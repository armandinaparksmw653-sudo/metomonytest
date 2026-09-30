module Main where

import Data.List (find)
import Metonymy.Contextual
import Metonymy.ContextualChecked
import Metonymy.ContextSpec
import Metonymy.GF
import Metonymy.Report (renderContractionReport, renderFiberReport)
import Metonymy.Snapshot
import Metonymy.Types
import System.Environment (getArgs)
import System.Exit (die)

pgfPath :: FilePath
pgfPath = "GeneratedMetonymy.pgf"

main :: IO ()
main = do
  arguments <- getArgs
  let contextualSnapshotPath = requestedSnapshotPath arguments
      contextualScenarioPath = requestedScenarioPath arguments
      formalFilteringEnabled = "--no-formal-filtering" `notElem` arguments
      commandArguments = stripContextualOptions arguments
  (qidSnapshot, _) <- loadSnapshot contextualSnapshotPath
  contextualScenarios <-
    loadContextScenarios qidSnapshot contextualScenarioPath
  case commandArguments of
    ["parse", sentence] -> runParse sentence
    ["linearize", tree] -> runLinearize tree
    ["contextual-fiber", scenarioName] ->
      case find ((== scenarioName) . contextScenarioName) contextualScenarios of
        Just scenario ->
          runContextualFiber formalFilteringEnabled qidSnapshot scenario
        Nothing -> die ("unknown contextual scenario: " <> scenarioName)
    ["contextual-contract", scenarioName, target] ->
      case find ((== scenarioName) . contextScenarioName) contextualScenarios of
        Just scenario ->
          runContextualContraction
            formalFilteringEnabled
            qidSnapshot
            scenario
            (EntityId target)
        Nothing -> die ("unknown contextual scenario: " <> scenarioName)
    _ -> usage

runContextualFiber :: Bool -> Snapshot -> ContextScenario -> IO ()
runContextualFiber formalFiltering snapshot scenario =
  case towerResult of
    Left message -> die ("contextual fiber failed: " <> message)
    Right stages -> do
      putStrLn ("graph_sha256=" <> snapshotHash snapshot)
      mapM_ putStrLn (renderFiberReport formalFiltering context stages)
  where
    context = contextScenarioContext scenario
    allowedRelations = contextScenarioRelations scenario
    maxDepth = contextScenarioMaxDepth scenario

    towerResult =
      if formalFiltering
        then contextualFiberChecked snapshot allowedRelations maxDepth context
        else contextualFiber snapshot allowedRelations maxDepth context

runContextualContraction ::
  Bool ->
  Snapshot ->
  ContextScenario ->
  EntityId ->
  IO ()
runContextualContraction formalFiltering snapshot scenario target =
  case
      if formalFiltering
        then
          contextualContractionChecked
            snapshot
            (contextScenarioRelations scenario)
            (contextScenarioMaxDepth scenario)
            (contextScenarioContext scenario)
            target
        else
          contextualContractionUnchecked
            snapshot
            (contextScenarioRelations scenario)
            (contextScenarioMaxDepth scenario)
            (contextScenarioContext scenario)
            target of
    Left message ->
      die ("contextual contraction rejected: " <> message)
    Right result -> do
      putStrLn ("graph_sha256=" <> snapshotHash snapshot)
      mapM_ putStrLn (renderContractionReport formalFiltering result)

runParse :: String -> IO ()
runParse sentence = do
  result <- parseEnglish pgfPath sentence
  case result of
    Left message -> die message
    Right trees -> mapM_ putStrLn trees

-- Diagnostic-only command: reveals what GeneratedMetonymyEng actually
-- linearizes a hand-built abstract tree to, so a compiles-but-doesn't-
-- parse mismatch (auxiliary/grammar/MetonymyEng.gf's own subordinate-
-- clause constructors, confirmed to fail this way three times in a row
-- on real CI runs -- see auxiliary/docs/contextual-tower.md) can be diagnosed directly
-- instead of guessed at from parser error positions alone.
runLinearize :: String -> IO ()
runLinearize tree = do
  result <- linearize pgfPath tree
  case result of
    Left message -> die message
    Right surface -> putStrLn surface

usage :: IO a
usage =
  die
    ( unlines
        [ "usage:"
        , "  metonymy parse \"English sentence\""
        , "  metonymy linearize \"GF abstract tree\"  # diagnostic only"
        , "  metonymy contextual-fiber SCENARIO"
        , "    [--snapshot PATH] [--scenarios PATH]"
        , "  metonymy contextual-contract SCENARIO TARGET-QID"
        , "    [--snapshot PATH] [--scenarios PATH]"
        ]
    )

requestedSnapshotPath :: [String] -> FilePath
requestedSnapshotPath = optionValue "--snapshot" "tower/data/wikidata-qid-snapshot"

requestedScenarioPath :: [String] -> FilePath
requestedScenarioPath = optionValue "--scenarios" "tower/data/contextual-scenarios.tsv"

optionValue :: String -> String -> [String] -> String
optionValue _ fallback [] = fallback
optionValue option fallback (name : value : rest)
  | name == option = value
  | otherwise = optionValue option fallback (value : rest)
optionValue _ fallback [_] = fallback

stripContextualOptions :: [String] -> [String]
stripContextualOptions [] = []
stripContextualOptions (name : _ : rest)
  | name `elem` ["--snapshot", "--scenarios"] =
      stripContextualOptions rest
stripContextualOptions (value : rest) =
  if value == "--no-formal-filtering"
    then stripContextualOptions rest
    else value : stripContextualOptions rest
