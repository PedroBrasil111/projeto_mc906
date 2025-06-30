# AI-Based Item Recommendation in League of Legends

This project explores the application of supervised learning techniques to recommend item builds in League of Legends, using match and timeline data from the Riot Games API.

## Dataset
- Collected from Riot's Developer API across multiple player tiers, mono-champions, and high-ranking players.
- JSON data parsed into two sets:
  - **Postgame**: final match stats per player.
  - **Timeline**: frame-by-frame match events.
- Includes features like champion one-hot encodings, player lane, perks, item OHE, game state (gold, objectives), and player KDA.

## Models
Four models were tested:
- **Random Forest**: interpretable but ignores item order and temporal context.
- **MLP**: uses static features for multi-label prediction of final 6 items.
- **RNN / LSTM**: temporal models that predict the next item per timeframe using timeline features. LSTM slightly outperforms RNN.

## Evaluation
Standard metrics were used:
- **Precision@6**, **Recall@6**
- **Micro and Macro F1 scores**

Additionally, custom sequential metrics were implemented:
- **Item Match Rate**: whether the predicted item appears in the ground truth build.
- **Relaxed Order Score**: penalizes predictions by how far off their position is.
- **Normalized Edit Distance**: how similar the predicted build is to the original.
- Predictions are averaged per match to reflect player-level accuracy.

## Key Observations
- LSTM performed best overall, capturing the temporal dynamics of item decisions.
- Models sometimes recommend items too early or repeat the same recommendation.
- Precision suffers when items are correct but appear out of order.

## Future Improvements
- Include gold and item cost as input features.
- Expand the dataset beyond current compute limitations.
- Penalize repeated or impossible item recommendations during training.
