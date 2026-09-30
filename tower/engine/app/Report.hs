-- | The main-workflow entry point: runs the curated example database
-- through the real, Agda-checked formal apparatus and prints the
-- per-layer tower breakdown for every example, one after another.
-- Exits non-zero (after printing every block, so a CI log always shows
-- the full picture) if any single example fails -- this is a real CI
-- gate, not just an information-printing step.
--
-- Covers 123 of the 124 curated examples individually: the 52
-- Haskell-module-driven ones from Metonymy.ExampleDatabase (15
-- flagship + 37 scale-tier -- see that module's docstring for the one
-- entry, the Rijeka+glass composition example, deliberately left out)
-- plus the 72 TSV-driven scale-tier scenarios from
-- tower/data/contextual-scenarios.tsv, loaded exactly as the
-- `contextual-fiber` CLI command already does via Metonymy.ContextSpec.
--
-- Usage: metonymy-report [--output FILE]
-- With --output, the report is written to FILE (and a one-line
-- "wrote N examples to FILE" note is still printed to stdout); without
-- it, the whole report goes to stdout.
module Main where

import Control.Monad (forM_)
import Metonymy.ContextSpec
import Metonymy.Contextual
import Metonymy.ContextualChecked
import Metonymy.ExampleDatabase
import Metonymy.Report (reconstructSentence, renderFiberReportLabeled)
import Metonymy.Snapshot
import System.Environment (getArgs)
import System.Exit (exitFailure)
import System.IO (IOMode (WriteMode), hPutStrLn, withFile)

-- | One example's outcome: the printable block, whether it passed, and
-- its name (for the final failure summary).
data Outcome = Outcome
  { outcomeReport :: String
  , outcomeOk :: Bool
  , outcomeName :: String
  }

main :: IO ()
main = do
  arguments <- getArgs
  (qidSnapshot, _) <- loadSnapshot "tower/data/wikidata-qid-snapshot"
  (containerSnapshot, _) <- loadSnapshot "tower/data/container-content-snapshot"
  scenarios <-
    loadContextScenarios qidSnapshot "tower/data/contextual-scenarios.tsv"
  let haskellOutcomes = map (renderExample qidSnapshot containerSnapshot) exampleDatabase
      tsvOutcomes = map (renderScenario qidSnapshot) scenarios
      allOutcomes = haskellOutcomes <> tsvOutcomes
      totalCount = length allOutcomes
      failedNames = [outcomeName o | o <- allOutcomes, not (outcomeOk o)]
  case outputPath arguments of
    Nothing -> forM_ allOutcomes (putStrLn . outcomeReport)
    Just path -> do
      withFile path WriteMode $ \handle ->
        forM_ allOutcomes (hPutStrLn handle . outcomeReport)
      putStrLn
        ( "wrote "
            <> show totalCount
            <> " examples to "
            <> path
        )
  if null failedNames
    then
      putStrLn
        ( "all "
            <> show totalCount
            <> " examples passed formal verification"
        )
    else do
      putStrLn
        ( show (length failedNames)
            <> " of "
            <> show totalCount
            <> " examples FAILED: "
            <> show failedNames
        )
      exitFailure

renderExample :: Snapshot -> Snapshot -> ExampleEntry -> Outcome
renderExample qidSnapshot containerSnapshot entryValue =
  Outcome
    { outcomeReport =
        unlines
          ( header
              : case result of
                Left message -> ["ERROR: " <> message]
                Right lines_ -> lines_
          )
    , outcomeOk = ok
    , outcomeName = exampleName entryValue
    }
  where
    header = "=== " <> exampleName entryValue <> " (" <> exampleTier entryValue <> ") ==="
    snapshot = exampleSnapshotOf qidSnapshot containerSnapshot entryValue
    context = exampleContextOf entryValue snapshot
    relations = exampleRelations entryValue
    depth = exampleMaxDepth entryValue

    kb = snapshotKnowledgeBase snapshot
    sentenceLine = "sentence=" <> show (reconstructSentence context)

    (result, ok) =
      case exampleContractionTarget entryValue of
        Nothing ->
          case contextualFiberChecked snapshot relations depth context of
            Left message -> (Left message, False)
            Right stages ->
              ( Right
                  ( renderFiberReportLabeled
                      True
                      kb
                      context
                      stages
                      (contextualCoarseReading snapshot relations context stages)
                  )
              , True
              )
        Just target ->
          case contextualContractionChecked snapshot relations depth context target of
            Left message ->
              -- A reject-test entry: rejection IS the expected, passing
              -- outcome.
              ( Right
                  [ sentenceLine
                  , "attempted contraction to " <> show target <> ": REJECTED (" <> message <> ")"
                  ]
              , True
              )
            Right _ ->
              -- The one genuinely bad outcome for a reject-test entry:
              -- it was supposed to be refused and wasn't.
              ( Right
                  [ sentenceLine
                  , "attempted contraction to " <> show target <> ": unexpectedly ACCEPTED"
                  ]
              , False
              )

renderScenario :: Snapshot -> ContextScenario -> Outcome
renderScenario snapshot scenario =
  Outcome
    { outcomeReport =
        unlines
          ( header
              : case result of
                Left message -> ["ERROR: " <> message]
                Right lines_ -> lines_
          )
    , outcomeOk = ok
    , outcomeName = contextScenarioName scenario
    }
  where
    header = "=== " <> contextScenarioName scenario <> " (scale, TSV) ==="
    context = contextScenarioContext scenario
    kb = snapshotKnowledgeBase snapshot
    (result, ok) =
      case contextualFiberChecked
        snapshot
        (contextScenarioRelations scenario)
        (contextScenarioMaxDepth scenario)
        context of
        Left message -> (Left message, False)
        Right stages ->
          ( Right
              ( renderFiberReportLabeled
                  True
                  kb
                  context
                  stages
                  ( contextualCoarseReading
                      snapshot
                      (contextScenarioRelations scenario)
                      context
                      stages
                  )
              )
          , True
          )

outputPath :: [String] -> Maybe String
outputPath ("--output" : path : _) = Just path
outputPath (_ : rest) = outputPath rest
outputPath [] = Nothing
