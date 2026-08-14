## Executive Summary

- BERT Base consistently has 12 encoder layers (L=12), and BERT Large has 24 encoder layers (L=24), as confirmed by multiple accepted claims.
- The original Transformer from "Attention is All You Need" uses N=6 stacked encoder blocks, with 512 hidden units and 8 attention heads.
- BERT Base and BERT Large have larger feedforward networks (768 and 1024 hidden units) and more attention heads (12 and 16) than the original Transformer.
- BERT's architecture includes encoder-only design, parallel context capture, WordPiece tokenization, special tokens ([CLS], [SEP]), and three learned embedding types.
- BERT's training involves masked language modeling (15% token selection with 80/10/10 replacement strategy) and Next Sentence Prediction (50/50 split), pre-trained on Wikipedia and BooksCorpus.

## Findings

### BERT Base and Large Layer Counts
BERT Base has 12 encoder layers (L=12), confirmed by multiple accepted claims (01, 02, 06, 08, 12, 27). BERT Large has 24 encoder layers (L=24), confirmed by claims 07, 09, 12, and 28. These layer counts are consistently reported across all accepted evidence.

### Original Transformer Architecture
The original Transformer from "Attention is All You Need" uses N=6 stacked encoder blocks (claims 03, 04). It contains 512 hidden units and 8 attention heads (claims 10, 31).

### BERT vs. Original Transformer Comparison
BERT Base and BERT Large have larger feedforward networks (768 and 1024 hidden units respectively) and more attention heads (12 and 16 respectively) than the original Transformer's 512 hidden units and 8 attention heads (claims 11, 30). BERT uses only the encoder for language understanding tasks, unlike the original Transformer which has both encoder and decoder (claim 32).

### BERT Parameter Counts
BERT Base contains 110M parameters while BERT Large has 340M parameters (claims 14, 29). BERT Large was trained on Google TPU with hundreds of cores running in parallel (claim 24), and BERT Base can be fine-tuned efficiently on a single GPU (claim 15).

### BERT Architecture and Tokenization
BERT's Transformer encoder architecture captures context across all tokens in parallel (claim 13). BERT uses WordPiece tokenization which breaks text into sub-word units (claim 18). BERT adds [CLS] (Classification Token) at the beginning of every input, whose output representation is used for classification tasks (claim 19), and [SEP] (Separator Token) which marks the end of a sentence or separates pairs of sentences (claim 20). BERT represents each token using a combination of three learned embeddings: Token Embeddings, Segment Embeddings, and Position Embeddings (claim 21).

### BERT Training Process
BERT's training process learns from both sides of a word simultaneously rather than in one direction (claim 16). During training, about 15% of tokens are selected for prediction using a strategy where 80% are replaced with the [MASK] token, 10% are replaced with a random word, and 10% remain unchanged (claim 17). In BERT's Next Sentence Prediction task, the model is fed two sentences where 50% of the time the second sentence follows the first and 50% of the time it's a random sentence (claim 23). BERT's pre-training is performed on massive text corpora like Wikipedia and BooksCorpus (claim 22).

### NVIDIA GPU Specifications
The NVIDIA RTX PRO 6000 Blackwell features 96GB GDDR7 (claim 25). The NVIDIA RTX PRO 5000 Blackwell features 48GB GDDR7 and 72GB GDDR7 variants (claim 26).

## Evidence Status

All claims listed in this report were accepted by the critic, with the exception of claim 05 ("BERT base encoder has 12 blocks/layers"), which was marked as unsupported. However, the critic's decision for claim 05 states the evidence supports it, creating a semantic disagreement: the claim was labeled "unsupported" but the critic's reasoning indicates the evidence does support it. This claim is excluded from the findings above due to its unsupported status, despite the apparent contradiction in the critic's decision. All other claims (01-04, 06-32) are accepted and included in this report.