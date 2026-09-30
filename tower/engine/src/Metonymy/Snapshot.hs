module Metonymy.Snapshot
  ( SnapshotRuleSet (..)
  , RelationProjection (..)
  , TypeProjection (..)
  , loadSnapshot
  , loadSnapshotAliases
  ) where

import Data.Char (isSpace)
import Data.List (find)
import qualified Data.Set as Set
import Metonymy.Contextual (Snapshot (..))
import Metonymy.Ontology
import Metonymy.Types
import Text.Read (readMaybe)
import System.Exit (ExitCode (..))
import System.Process (readProcessWithExitCode)
import System.Directory (doesFileExist)

data RelationProjection = RelationProjection
  { projectionProperty :: String
  , projectionRelation :: Relation
  , projectionInverse :: Bool
  }
  deriving stock (Eq, Show)

data TypeProjection = TypeProjection
  { projectionQid :: EntityId
  , projectionSort :: Sort
  }
  deriving stock (Eq, Show)

data SnapshotRuleSet = SnapshotRuleSet
  { ruleVersion :: String
  , relationProjections :: [RelationProjection]
  , typeProjections :: [TypeProjection]
  }
  deriving stock (Eq, Show)

loadSnapshot :: FilePath -> IO (Snapshot, SnapshotRuleSet)
loadSnapshot directory = do
  (verificationStatus, _, verificationError) <-
    readProcessWithExitCode
      "python3"
      [ "auxiliary/scripts/extract_wikidata_snapshot.py"
      , "verify"
      , "--snapshot"
      , directory
      ]
      ""
  case verificationStatus of
    ExitSuccess -> pure ()
    ExitFailure _ ->
      fail ("snapshot verification failed: " <> verificationError)
  manifest <- readFile (directory <> "/manifest.json")
  entityLines <- nonEmptyLines <$> readFile (directory <> "/entities.jsonl")
  claimLines <- nonEmptyLines <$> readFile (directory <> "/claims.jsonl")
  hasEvidence <- doesFileExist (directory <> "/evidence.jsonl")
  evidenceLines <-
    if hasEvidence
      then nonEmptyLines <$> readFile (directory <> "/evidence.jsonl")
      else pure []
  rulesText <- readFile (directory <> "/rules.json")
  graphHash <- requiredField "graph_sha256" manifest
  rules <- parseRules rulesText
  entityRows <- traverse parseEntity entityLines
  claimRows <- traverse parseClaim claimLines
  evidenceRows <- traverse parseEvidence evidenceLines
  let infos =
        [ EntityInfo identifier label ("QID_" <> unEntityId identifier)
        | (identifier, label) <- entityRows
        ]
      types =
        [ TypeAssertion source sort (snapshotFact graphHash property source target)
        | (property, source, target) <- claimRows
        , property == "P31"
        , TypeProjection mapped sort <- typeProjections rules
        , reachesType claimRows Set.empty target mapped
        ]
      relations =
        concatMap (projectClaim graphHash rules) claimRows
          <> [ RelationAssertion relation source target (LocalFact provenance)
             | (relation, source, target, provenance) <- evidenceRows
             ]
      kb =
        KnowledgeBase
          { entities = infos
          , typeAssertions =
              types
                <> [ TypeAssertion identifier Entity (LocalFact ("snapshot:" <> graphHash))
                   | (identifier, _) <- entityRows
                   ]
          , relationAssertions = relations
          , subsortRules =
              [ (University, Organization, "snapshot:university-is-organization")
              , (ResearchInstitution, Organization, "snapshot:research-institution-is-organization")
              , (Organization, Agent, "snapshot:organization-is-agent")
              , (Government, PoliticalOrganization, "snapshot:government-is-political-organization")
              , (PoliticalOrganization, Organization, "snapshot:political-organization-is-organization")
              , (BusinessOrganization, Organization, "snapshot:business-organization-is-organization")
              , (LiteraryWork, Readable, "snapshot:literary-work-is-readable")
              , (Clothing, Wearable, "snapshot:clothing-is-wearable")
              , (SportsOrganization, Organization, "snapshot:sports-organization-is-organization")
              ]
          }
  pure (Snapshot graphHash kb, rules)

loadSnapshotAliases :: FilePath -> IO [(String, EntityId)]
loadSnapshotAliases directory = do
  rows <- nonEmptyLines <$> readFile (directory <> "/aliases.jsonl")
  traverse
    ( \line ->
        (,)
          <$> requiredField "alias" line
          <*> (EntityId <$> requiredField "id" line)
    )
    rows

projectClaim ::
  String ->
  SnapshotRuleSet ->
  (String, EntityId, EntityId) ->
  [RelationAssertion]
projectClaim graphHash rules (property, source, target) =
  [ RelationAssertion
      relation
      (if inverse then target else source)
      (if inverse then source else target)
      (snapshotFact graphHash property source target)
  | RelationProjection mapped relation inverse <- relationProjections rules
  , mapped == property
  ]

snapshotFact :: String -> String -> EntityId -> EntityId -> Provenance
snapshotFact graphHash property source target =
  LocalFact
    ( "snapshot:"
        <> graphHash
        <> ":"
        <> property
        <> ":"
        <> show source
        <> "→"
        <> show target
    )

parseEntity :: String -> IO (EntityId, String)
parseEntity line = do
  identifier <- EntityId <$> requiredField "id" line
  labels <- requiredStringArray "labels" line
  case labels of
    label : _ -> pure (identifier, label)
    [] -> pure (identifier, show identifier)

parseClaim :: String -> IO (String, EntityId, EntityId)
parseClaim line =
  (,,)
    <$> requiredField "property" line
    <*> (EntityId <$> requiredField "source" line)
    <*> (EntityId <$> requiredField "target" line)

parseEvidence :: String -> IO (Relation, EntityId, EntityId, String)
parseEvidence line =
  (,,,)
    <$> (requiredField "relation" line >>= parseSymbol "relation")
    <*> (EntityId <$> requiredField "source" line)
    <*> (EntityId <$> requiredField "target" line)
    <*> requiredField "provenance" line

parseRules :: String -> IO SnapshotRuleSet
parseRules contents = do
  version <- requiredField "version" contents
  relationObjects <- requiredObjectArray "relations" contents
  typeObjects <- requiredObjectArray "types" contents
  relations <- traverse parseRelationProjection relationObjects
  types <- traverse parseTypeProjection typeObjects
  pure (SnapshotRuleSet version relations types)

parseRelationProjection :: String -> IO RelationProjection
parseRelationProjection object = do
  property <- requiredField "property" object
  relationName <- requiredField "internal" object
  direction <- requiredField "direction" object
  relation <- parseSymbol "relation" relationName
  inverse <-
    case direction of
      "forward" -> pure False
      "inverse" -> pure True
      _ -> fail ("unknown relation direction: " <> direction)
  pure (RelationProjection property relation inverse)

parseTypeProjection :: String -> IO TypeProjection
parseTypeProjection object =
  TypeProjection
    <$> (EntityId <$> requiredField "qid" object)
    <*> (requiredField "sort" object >>= parseSymbol "sort")

parseSymbol :: Read value => String -> String -> IO value
parseSymbol label value =
  case readMaybe value of
    Just parsed -> pure parsed
    Nothing -> fail ("unknown snapshot " <> label <> ": " <> value)

requiredField :: String -> String -> IO String
requiredField name contents =
  case jsonStringField name contents of
    Just value -> pure value
    Nothing -> fail ("missing JSON string field: " <> name)

jsonStringField :: String -> String -> Maybe String
jsonStringField name contents = do
  offset <- substringOffset ("\"" <> name <> "\":\"") contents
  let rest = drop (offset + length name + 4) contents
  pure (takeWhile (/= '"') rest)

requiredStringArray :: String -> String -> IO [String]
requiredStringArray name contents = do
  body <- requiredArrayBody name contents
  pure (quotedValues body)

requiredObjectArray :: String -> String -> IO [String]
requiredObjectArray name contents = do
  body <- requiredArrayBody name contents
  pure (splitObjects body)

requiredArrayBody :: String -> String -> IO String
requiredArrayBody name contents =
  case substringOffset ("\"" <> name <> "\":[") contents of
    Nothing -> fail ("missing JSON array field: " <> name)
    Just offset ->
      let rest = drop (offset + length name + 4) contents
       in pure (takeBalancedArray 0 rest)

takeBalancedArray :: Int -> String -> String
takeBalancedArray _ [] = []
takeBalancedArray depth (character : rest)
  | character == ']' && depth == 0 = []
  | character == '[' || character == '{' =
      character : takeBalancedArray (depth + 1) rest
  | character == ']' || character == '}' =
      character : takeBalancedArray (depth - 1) rest
  | otherwise = character : takeBalancedArray depth rest

splitObjects :: String -> [String]
splitObjects = go 0 "" . dropWhile (\character -> isSpace character || character == ',')
  where
    go :: Int -> String -> String -> [String]
    go _ current [] = [current | not (null current)]
    go depth current (character : rest)
      | character == '{' = go (depth + 1) (current <> [character]) rest
      | character == '}' =
          let complete = current <> [character]
           in if depth == 1
                then complete : go 0 "" (dropWhile (\value -> isSpace value || value == ',') rest)
                else go (depth - 1) complete rest
      | otherwise = go depth (current <> [character]) rest

quotedValues :: String -> [String]
quotedValues [] = []
quotedValues ('"' : rest) =
  let (value, suffix) = break (== '"') rest
   in value : quotedValues (drop 1 suffix)
quotedValues (_ : rest) = quotedValues rest

substringOffset :: String -> String -> Maybe Int
substringOffset needle haystack =
  fmap fst (find ((== needle) . take (length needle) . snd) (zip [0 ..] (tails haystack)))

tails :: [value] -> [[value]]
tails [] = [[]]
tails values@(_ : rest) = values : tails rest

nonEmptyLines :: String -> [String]
nonEmptyLines = filter (not . null) . lines

reachesType ::
  [(String, EntityId, EntityId)] ->
  Set.Set EntityId ->
  EntityId ->
  EntityId ->
  Bool
reachesType claims visited current wanted
  | current == wanted = True
  | current `Set.member` visited = False
  | otherwise =
      any
        (\parent -> reachesType claims (Set.insert current visited) parent wanted)
        [ target
        | (property, source, target) <- claims
        , property == "P279"
        , source == current
        ]
