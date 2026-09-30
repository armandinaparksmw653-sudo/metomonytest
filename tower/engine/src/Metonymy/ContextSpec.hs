module Metonymy.ContextSpec
  ( ContextScenario (..)
  , loadContextScenarios
  ) where

import Metonymy.Contextual
import Metonymy.Types
import Text.Read (readMaybe)

data ContextScenario = ContextScenario
  { contextScenarioName :: String
  , contextScenarioContext :: Context
  , contextScenarioRelations :: [Relation]
  , contextScenarioMaxDepth :: Int
  }
  deriving stock (Eq, Show)

loadContextScenarios :: Snapshot -> FilePath -> IO [ContextScenario]
loadContextScenarios snapshot path = do
  contents <- readFile path
  case lines contents of
    [] -> fail ("empty contextual scenario file: " <> path)
    header : rows
      | header /= expectedHeader ->
          fail ("unexpected contextual scenario header: " <> path)
      | otherwise -> traverse parseRow (zip [2 :: Int ..] rows)
  where
    parseRow (lineNumber, row) =
      case splitTabs row of
        [name, source, action, role, maxDepth, relationText, constraintText] -> do
          parsedRole <- parseAt lineNumber role
          parsedDepth <- parseAt lineNumber maxDepth
          parsedRelations <- traverse (parseAt lineNumber) (splitComma relationText)
          constraints <- traverse (parseConstraint lineNumber) (splitDoubleSemicolon constraintText)
          let tree =
                LexicalApply
                  "ContextFixture"
                  [ LexicalLeaf (constraintOrigin constraint) [constraintPayload constraint]
                  | constraint <- constraints
                  ]
              context =
                Context
                  { contextTree = tree
                  , contextSnapshotHash = snapshotHash snapshot
                  , contextSource = EntityId source
                  , contextAction = action
                  , contextRole = parsedRole
                  , contextConstraints = constraints
                  , contextRuleProvenance =
                      map constraintProvenance constraints
                  }
          pure
            ContextScenario
              { contextScenarioName = name
              , contextScenarioContext = context
              , contextScenarioRelations = parsedRelations
              , contextScenarioMaxDepth = parsedDepth
              }
        _ -> failAt lineNumber "expected seven tab-separated fields"

    parseConstraint lineNumber encoded =
      case splitPipe encoded of
        [constructor, lemma, surface, start, end, "requires", requirement, provenance] ->
          ContextConstraint
            <$> ( LexicalAnchor constructor lemma surface
                    <$> parseAt lineNumber start
                    <*> parseAt lineNumber end
                )
            <*> (Requires <$> parseAt lineNumber requirement)
            <*> pure provenance
        [constructor, lemma, surface, start, end, "relation", relation, target, provenance] ->
          ContextConstraint
            <$> ( LexicalAnchor constructor lemma surface
                    <$> parseAt lineNumber start
                    <*> parseAt lineNumber end
                )
            <*> (RequiresRelation <$> parseAt lineNumber relation <*> pure (EntityId target))
            <*> pure provenance
        [constructor, lemma, surface, start, end, "some", relation, requirement, provenance] ->
          ContextConstraint
            <$> ( LexicalAnchor constructor lemma surface
                    <$> parseAt lineNumber start
                    <*> parseAt lineNumber end
                )
            <*> (RequiresSome <$> parseAt lineNumber relation <*> parseAt lineNumber requirement)
            <*> pure provenance
        [constructor, lemma, surface, start, end, "prefers", requirement, provenance] ->
          ContextConstraint
            <$> ( LexicalAnchor constructor lemma surface
                    <$> parseAt lineNumber start
                    <*> parseAt lineNumber end
                )
            <*> (Prefers <$> parseAt lineNumber requirement)
            <*> pure provenance
        [constructor, lemma, surface, start, end, "prefers-relation", relation, target, provenance] ->
          ContextConstraint
            <$> ( LexicalAnchor constructor lemma surface
                    <$> parseAt lineNumber start
                    <*> parseAt lineNumber end
                )
            <*> (PrefersRelation <$> parseAt lineNumber relation <*> pure (EntityId target))
            <*> pure provenance
        [constructor, lemma, surface, start, end, "prefers-some", relation, requirement, provenance] ->
          ContextConstraint
            <$> ( LexicalAnchor constructor lemma surface
                    <$> parseAt lineNumber start
                    <*> parseAt lineNumber end
                )
            <*> (PrefersSome <$> parseAt lineNumber relation <*> parseAt lineNumber requirement)
            <*> pure provenance
        _ -> failAt lineNumber ("malformed contextual constraint: " <> encoded)

    parseAt lineNumber value =
      case readMaybe value of
        Just parsed -> pure parsed
        Nothing -> failAt lineNumber ("unknown symbolic value: " <> value)

    failAt lineNumber message =
      fail (path <> ":" <> show lineNumber <> ": " <> message)

expectedHeader :: String
expectedHeader =
  "scenario\tsource_qid\taction\trole\tmax_depth\tbridge_relations\tconstraints"

splitTabs :: String -> [String]
splitTabs = splitOn '\t'

splitComma :: String -> [String]
splitComma = splitOn ','

splitPipe :: String -> [String]
splitPipe = splitOn '|'

splitOn :: Char -> String -> [String]
splitOn delimiter value =
  case break (== delimiter) value of
    (field, []) -> [field]
    (field, _ : rest) -> field : splitOn delimiter rest

splitDoubleSemicolon :: String -> [String]
splitDoubleSemicolon value =
  case breakPair value of
    (field, Nothing) -> [field]
    (field, Just rest) -> field : splitDoubleSemicolon rest
  where
    breakPair [] = ([], Nothing)
    breakPair (';' : ';' : rest) = ([], Just rest)
    breakPair (character : rest) =
      let (prefix, suffix) = breakPair rest
       in (character : prefix, suffix)
