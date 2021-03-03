import json
import os
import time

from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from pathlib import Path


def main():

    ###########################################################################
    #              BEFORE RUNNING THE SCRIPT SET THE VALUES BELOW
    ###########################################################################

    # REQUIRED
    # --------
    # Elements RPC Credentials
    # You need to change all 3 after setting them in your elements.conf file.
    # See associated README for example config file format.
    RPC_USER = 'yourusernamehere'
    RPC_PASSWORD = 'yourpasswordhere'
    RPC_PORT = 18884
    RPC_USER = 'user5145017847548301'
    RPC_PASSWORD = 'password7400934705786065'
    RPC_PORT = 18884

    # OPTIONAL
    # --------
    # Set the following to an asset hex if you want to report on a specific
    # asset, otherwise leave it as None to report on all assets:
    ASSET_ID = None

    # OPTIONAL
    # --------
    # The script appends to file so if you run the script once, you can start
    # again at the last block height processed. The last block processed will
    # be saved in the file LAST_BLOCK after the script has run. 0 start from
    # genesis:
    START_AT_BLOCK_HEIGHT = 0

    # OPTIONAL
    # --------
    # Stop processing at a particular block height (inclusive).
    # Set to None to process until chain tip:
    STOP_AT_BLOCK_HEIGHT = None

    ###########################################################################
    #              BEFORE RUNNING THE SCRIPT SET THE VALUES ABOVE
    ###########################################################################

    block_count = 0
    block_hash = ''
    rpc_ready = False
    end_of_chain = False
    block_height = START_AT_BLOCK_HEIGHT

    # Delete asset files if we are starting from genesis:
    if START_AT_BLOCK_HEIGHT == 0:
        removeAssetFiles()

    # Check node is ready for RPC calls
    while not rpc_ready:
        try:
            rpc_connection = AuthServiceProxy(f'http://{RPC_USER}:{RPC_PASSWORD}@127.0.0.1:{RPC_PORT}')
            block_count = rpc_connection.getblockcount()
            rpc_ready = True
        except Exception as e:
            print(f'Cannot connect to node or node not ready for RPC: {e}')
            print('Sleeping for 5 seconds...')
            time.sleep(5)

    print('Connected to node using RPC')

    while not end_of_chain:
        try:
            print(f'Trying to process block at height {block_height}')
            block_hash = rpc_connection.getblockhash(block_height)
            block = rpc_connection.getblock(block_hash)
            last_existing_block = block_height
            txs = block['tx']

            for tx in txs:
                tx_hash = rpc_connection.getrawtransaction(tx)
                tx_details = rpc_connection.decoderawtransaction(tx_hash)

                #Issuances and Reissuances:
                for vin in tx_details['vin']:
                    issuance = vin.get('issuance')
                    if issuance:
                        if ASSET_ID is None or ASSET_ID == issuance['asset']:
                            writeIssueOrReissue(issuance, block_height)
                #Burns:
                for vout in tx_details['vout']:
                    vout_value = str(vout.get('value', '0E-8'))
                    if vout_value != '0.00000000' and vout_value != '0E-8':
                        script_pubkey = vout.get('scriptPubKey')
                        if script_pubkey:
                            asm = script_pubkey.get('asm')
                            script_type = script_pubkey.get('type')
                            if asm and script_type:
                                if asm == 'OP_RETURN' and script_type == 'nulldata':
                                    if ASSET_ID is None or ASSET_ID == vout['asset']:
                                        writeBurn(vout, block_height)
            if STOP_AT_BLOCK_HEIGHT:
                if STOP_AT_BLOCK_HEIGHT == block_height:
                    end_of_chain = True
            block_height = block_height + 1
        except Exception as e:
            if hasattr(e, 'message'):
                if e.message == 'Block height out of range':
                    print(f'No block at height {block_height}. Reached chain tip. Stopping.')
                else:
                    print(f'Error: {e.message}')
            else:
                print(f'Error: {e}')
            end_of_chain = True
    print(f'Last block processed was at height {last_existing_block}. Saved last block height to "LAST_BLOCK" file.')
    writeLastBlock(last_existing_block)

def writeLastBlock(block_height):
    with open(f'LAST_BLOCK', 'w') as filetowrite:
        filetowrite.write(str(block_height))

def writeBurn(burn, block_height):
    Path('assets').mkdir(parents=True, exist_ok=True)
    asset_hex = burn['asset']
    with open(f'assets/{asset_hex}', 'a') as filetowrite:
        amount = burn['value']
        action = 'BURN'
        filetowrite.write(f'{action}\n')
        filetowrite.write('-' * len(action))
        filetowrite.write('\n')
        filetowrite.write(f'Asset Hex: {asset_hex}\n')
        filetowrite.write(f'Amount: {amount}\n')
        filetowrite.write(f'Block: {block_height}\n')
        filetowrite.write('\n')

def writeIssueOrReissue(issuance, block_height):
    Path('assets').mkdir(parents=True, exist_ok=True)
    asset_hex = issuance['asset']
    with open(f'assets/{asset_hex}', 'a') as filetowrite:
        asset_amount_type = 'Asset Amount'
        token_amount_type = 'Token Amount'
        token_amount = 0
        issuance_type = None

        token_hex = issuance.get('token')
        is_reissuance = issuance['isreissuance']

        # If there is no assetamount the issuance was blinded
        asset_amount = issuance.get('assetamount')
        if asset_amount:
            issuance_type = 'Unblinded'
        else:
            asset_amount = issuance.get('assetamountcommitment')
            if asset_amount:
                asset_amount_type = 'Asset Amount Commitment'
                issuance_type = 'Blinded'

        if not is_reissuance:
            # If there is no tokenamount the issuance was blinded
            token_amount = issuance.get('tokenamount')
            if not token_amount:
                if asset_amount_type == 'Asset Amount Commitment':
                    token_amount_type = 'Token Amount Commitment'
                token_amount = issuance.get('tokenamountcommitment', 0)

        if is_reissuance:
            issuance_reissuance = 'REISSUANCE'
        else:
            issuance_reissuance = 'ISSUANCE'
        filetowrite.write(f'{issuance_reissuance} ({issuance_type})\n')
        filetowrite.write('-' * len(f'{issuance_reissuance} ({issuance_type})'))
        filetowrite.write('\n')
        filetowrite.write(f'Asset Hex: {asset_hex}\n')
        if not is_reissuance:
            filetowrite.write(f'Token Hex: {token_hex}\n')
        filetowrite.write(f'{asset_amount_type}: {str(asset_amount)}\n')
        if not is_reissuance:
            if token_amount:
                filetowrite.write(f'{token_amount_type}: {str(token_amount)}\n')
            else:
                filetowrite.write(f'{token_amount_type}: {0}\n')
        filetowrite.write(f'Block: {block_height}\n')
        filetowrite.write('\n')

def removeAssetFiles():
    folder = 'assets'
    Path('assets').mkdir(parents=True, exist_ok=True)
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))


if __name__ == '__main__':
    main()
