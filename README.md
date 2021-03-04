# elements-asset-balance-verify
Searches Elements blocks for issuances, reissuances, burns of an asset to provide supply total.

Before running, set values as directed in the script.

## Example

This asset: https://blockstream.info/liquid/asset/f266a3f15e78b71481adfedff9aefe47c69501a181ffc68527bb5fb26da6a4b2

Was issued in transaction: https://blockstream.info/liquid/tx/49cc1ca72be5b5ca3375348274cee22ccb686f4c3a8f8bc7767156680ca61d92

Which was included in block: 1038078

To process every tx in every block since issuance to check for any reissuances
or burns for the asset so you can validate the amounts shown on the liquid
assets page above.You can run the script with:

```
ASSET_ID = 'f266a3f15e78b71481adfedff9aefe47c69501a181ffc68527bb5fb26da6a4b2'
START_BLOCK_HEIGHT = 1038078
STOP_AT_BLOCK_HEIGHT = None
```

## Config

Your elements node must have txindex=1 in elements.conf. If it doesn't you need to add it to your confiog file and start elements with the ``--reindex`` argument once so it indexs the blockchain. After adding the config file setting and reindexing once, you can start elements normally from then on. If you do not do this the script will fail with an error: ``Error: No such mempool or blockchain transaction. Use gettransaction for wallet transactions.``.

Example elements.conf for the live Liquid livuidv1 network (you must change the rpc* values below):

```
rpcuser=yourrpcusername
rpcpassword=yourrpcpassword
[liquidv1]
rpcport=yourrpcport
daemon=1
server=1
listen=1
txindex=1
fallbackfee=0.00000100
```

## Install and run

To install requirements and run the script (Linux):

```
virtualenv -p python3 venv

source venv/bin/activate

pip install python-bitcoinrpc

python elements-asset-balance-verify.py
```

## Example Output

Example outputs using a local elementsregtest blockchain for demo purposes (any locally connected node will report the same details, regardless of which node issued, reissused or burned the asset):

Output to file assets/b2e15d0d7a0c94e4e2ce0fe6e8691b9e451377f6e46e8045a86f7c4b5d4f0f23:

```
ISSUANCE (Unblinded)
--------------------
Asset Hex: b2e15d0d7a0c94e4e2ce0fe6e8691b9e451377f6e46e8045a86f7c4b5d4f0f23
Token Hex: a6be6b365498cd451be75ba0f68c258ee01e08f3cb30d5f8469f6628db58dc61
Asset Amount: 21000000.00000000
Token Amount: 0
Block: 0
```

Output to file assets/9b59712ae37518fcaa13cbaf3f136e17cd8968c4e0cba9e323e5970dcc18a5c3:

```
ISSUANCE (Unblinded)
--------------------
Asset Hex: 9b59712ae37518fcaa13cbaf3f136e17cd8968c4e0cba9e323e5970dcc18a5c3
Token Hex: 7d6b3dbad4f68b61ecfc9a76657037b606b7262e9c253811a4cf0b0bf6aae2e9
Asset Amount: 555.00000000
Token Amount: 1.00000000
Block: 5

REISSUANCE (Unblinded)
----------------------
Asset Hex: 9b59712ae37518fcaa13cbaf3f136e17cd8968c4e0cba9e323e5970dcc18a5c3
Asset Amount: 9.00000000
Block: 6

BURN
----
Asset Hex: 9b59712ae37518fcaa13cbaf3f136e17cd8968c4e0cba9e323e5970dcc18a5c3
Amount: 7.00000000
Block: 8
```

Output to file assets/0c28580034fbce24ad994950ed7df77ebcb9e78f4e8d795f5516f5d58012a6e7:

```
ISSUANCE (Blinded)
------------------
Asset Hex: 0c28580034fbce24ad994950ed7df77ebcb9e78f4e8d795f5516f5d58012a6e7
Token Hex: 4681c7787707860b27ad55d585f09e3f4066fca4e9f2914e191dd489578391a7
Asset Amount Commitment: 08e66b5681433cf5fbf16613185b5da6fbbbc9591047507b062c3c8e7d40c6ceb4
Token Amount Commitment: 082fed56de34400ef22ee4ef32ccaca1bf54644954ec5e18ed57e00179add4854a
Block: 4

REISSUANCE (Blinded)
--------------------
Asset Hex: 0c28580034fbce24ad994950ed7df77ebcb9e78f4e8d795f5516f5d58012a6e7
Asset Amount Commitment: 096df295348063d9b09cc2b5144f2a4a70599eb9c19c27bb5f3b6412d768cab41f
Block: 7

BURN
----
Asset Hex: 0c28580034fbce24ad994950ed7df77ebcb9e78f4e8d795f5516f5d58012a6e7
Amount: 1.00000000
Block: 9

BURN
----
Asset Hex: 0c28580034fbce24ad994950ed7df77ebcb9e78f4e8d795f5516f5d58012a6e7
Amount: 2.00000000
Block: 10
```
