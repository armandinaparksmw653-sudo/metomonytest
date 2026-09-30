module Metonymy.Elaborator
  ( ElaborationError (..)
  , LexicalBinding (..)
  , lexicalizeGFTree
  , elaborateContext
  ) where

import Metonymy.Contextual
import Metonymy.Types
import Data.List (find)

data ElaborationError
  = UnsupportedConstruction String
  | InvalidElaboratedContext String
  | MalformedGFTree String
  | MissingLexicalBinding String
  | SurfaceTokenMissing String
  deriving stock (Eq, Show)

data LexicalBinding = LexicalBinding
  { bindingGFConstructor :: String
  , bindingLemma :: String
  , bindingSurface :: String
  , bindingPayloads :: [ConstraintPayload]
  }
  deriving stock (Eq, Show)

lexicalizeGFTree ::
  String ->
  [LexicalBinding] ->
  String ->
  Either ElaborationError LexicalTree
lexicalizeGFTree sentence bindings sourceTree = do
  (tree, remaining) <- parseExpression 0 (tokens sourceTree)
  case filter (`notElem` ["(", ")"]) remaining of
    [] -> Right tree
    rest -> Left (MalformedGFTree ("unconsumed tokens: " <> unwords rest))
  where
    parseExpression offset rawTokens =
      case dropOpening rawTokens of
        [] -> Left (MalformedGFTree "unexpected end of GF tree")
        constructor : rest ->
          case lexicalStringArity constructor of
            Just stringCount -> parseStringLexeme offset constructor stringCount rest
            Nothing -> case arity constructor of
              Just childCount -> do
                (children, suffix, _) <-
                  parseChildren childCount offset rest
                pure
                  ( LexicalApply constructor children
                  , dropClosing suffix
                  )
              Nothing -> do
                binding <-
                  maybe
                    (Left (MissingLexicalBinding constructor))
                    Right
                    (find ((== constructor) . bindingGFConstructor) bindings)
                start <-
                  maybe
                    (Left (SurfaceTokenMissing (bindingSurface binding)))
                    Right
                    (substringOffsetFrom offset (bindingSurface binding) sentence)
                let end = start + length (bindingSurface binding)
                    anchor =
                      LexicalAnchor
                        constructor
                        (bindingLemma binding)
                        (bindingSurface binding)
                        start
                        end
                pure
                  ( LexicalLeaf anchor (bindingPayloads binding)
                  , dropClosing rest
                  )

    parseStringLexeme offset constructor stringCount rest =
      let (arguments, suffix) = splitAt stringCount rest
       in if length arguments /= stringCount
            then Left (MalformedGFTree ("missing string arguments for " <> constructor))
            else do
              let binding =
                    find ((== constructor) . bindingGFConstructor) bindings
                  lexicalValue =
                    maybe
                      (stripQuotes (head arguments))
                      bindingSurface
                      binding
                  lemma =
                    maybe
                      (stripQuotes (head arguments))
                      bindingLemma
                      binding
                  payloads = maybe [] bindingPayloads binding
              start <-
                maybe
                  (Left (SurfaceTokenMissing lexicalValue))
                  Right
                  (substringOffsetFrom offset lexicalValue sentence)
              let anchor =
                    LexicalAnchor
                      constructor
                      lemma
                      lexicalValue
                      start
                      (start + length lexicalValue)
              pure (LexicalLeaf anchor payloads, dropClosing suffix)

    parseChildren 0 offset remaining = Right ([], remaining, offset)
    parseChildren count offset remaining = do
      let next = dropOpening remaining
      (child, suffix) <- parseExpression offset next
      let nextOffset = maximum (offset : map anchorEnd (treeAnchors child))
      (children, finalSuffix, finalOffset) <-
        parseChildren (count - 1) nextOffset suffix
      pure (child : children, finalSuffix, finalOffset)

arity :: String -> Maybe Int
arity "Pred" = Just 2
arity "Compl" = Just 2
arity "NP" = Just 1
arity "PP" = Just 2
arity "ModIn" = Just 2
arity "Negate" = Just 1
arity "Quantify" = Just 2
arity "NegPred" = Just 2
arity "InPP" = Just 1
arity "AboutPP" = Just 1
arity "WithPP" = Just 1
arity "ForPP" = Just 1
arity "ModifyNP" = Just 2
arity "ModifyRel" = Just 3
arity "IndefCN" = Just 1
arity "DefCN" = Just 1
arity "ModifyRelCN" = Just 3
arity "EveryCN" = Just 2
arity _ = Nothing

lexicalStringArity :: String -> Maybe Int
lexicalStringArity "OpenPN" = Just 1
lexicalStringArity "OpenIndefCN" = Just 2
lexicalStringArity "OpenDefCN" = Just 2
lexicalStringArity "EveryCN" = Just 2
lexicalStringArity _ = Nothing

tokens :: String -> [String]
tokens = reverse . finish . foldl step (False, "", [])
  where
    step (quoted, current, result) character
      | character == '"' =
          (not quoted, current <> [character], result)
      | quoted =
          (quoted, current <> [character], result)
      | character == '(' || character == ')' =
          (False, "", [character] : flush current result)
      | character == ' ' || character == '\t' || character == '\n' =
          (False, "", flush current result)
      | otherwise =
          (False, current <> [character], result)

    flush "" result = result
    flush current result = current : result

    finish (_, current, result) = flush current result

stripQuotes :: String -> String
stripQuotes value
  | length value >= 2 && head value == '"' && last value == '"' =
      init (tail value)
  | otherwise = value

dropOpening :: [String] -> [String]
dropOpening ("(" : rest) = rest
dropOpening values = values

dropClosing :: [String] -> [String]
dropClosing (")" : rest) = rest
dropClosing values = values

substringOffsetFrom :: Int -> String -> String -> Maybe Int
substringOffsetFrom offset needle haystack =
  fmap (+ offset) (search needle (drop offset haystack))
  where
    search _ [] = Nothing
    search wanted remaining
      | take (length wanted) remaining == wanted = Just 0
      | otherwise = fmap (+ 1) (search wanted (drop 1 remaining))

treeAnchors :: LexicalTree -> [LexicalAnchor]
treeAnchors (LexicalLeaf anchor _) = [anchor]
treeAnchors (LexicalApply _ children) = concatMap treeAnchors children

elaborateContext ::
  String ->
  EntityId ->
  String ->
  HoleRole ->
  LexicalTree ->
  Either ElaborationError Context
elaborateContext snapshotHash source action role tree = do
  validateTree tree
  let context =
        Context
          { contextTree = tree
          , contextSnapshotHash = snapshotHash
          , contextSource = source
          , contextAction = action
          , contextRole = role
          , contextConstraints = collectConstraints tree
          , contextRuleProvenance =
              map constraintProvenance (collectConstraints tree)
          }
  case validateContext context of
    Left message -> Left (InvalidElaboratedContext message)
    Right () -> Right context

validateTree :: LexicalTree -> Either ElaborationError ()
validateTree (LexicalLeaf _ _) = Right ()
validateTree (LexicalApply constructor children)
  | constructor `elem` supportedConstructions =
      traverse_ validateTree children
  | otherwise = Left (UnsupportedConstruction constructor)

supportedConstructions :: [String]
supportedConstructions =
  [ "Pred"
  , "Compl"
  , "NP"
  , "PP"
  , "Negate"
  , "Quantify"
  , "NegPred"
  , "InPP"
  , "AboutPP"
  , "WithPP"
  , "ForPP"
  , "ModifyNP"
  , "ModifyRel"
  , "IndefCN"
  , "DefCN"
  , "ModifyRelCN"
  , "EveryCN"
  ]

collectConstraints :: LexicalTree -> [ContextConstraint]
collectConstraints (LexicalLeaf anchor payloads) =
  map (\payload -> ContextConstraint anchor payload "lexical-tree") payloads
collectConstraints (LexicalApply _ children) =
  concatMap collectConstraints children

traverse_ :: (value -> Either error ()) -> [value] -> Either error ()
traverse_ _ [] = Right ()
traverse_ check (value : values) = do
  check value
  traverse_ check values
