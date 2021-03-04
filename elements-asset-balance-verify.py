import json
import os
import sys
import time

from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from pathlib import Path


def main():

    # Example
    # -------
    # This asset: https://blockstream.info/liquid/asset/f266a3f15e78b71481adfedff9aefe47c69501a181ffc68527bb5fb26da6a4b2
    # Was issued in transaction: https://blockstream.info/liquid/tx/49cc1ca72be5b5ca3375348274cee22ccb686f4c3a8f8bc7767156680ca61d92
    # Which was included in block: 1038078
    # You can run the script with:
    # ASSET_ID = 'f266a3f15e78b71481adfedff9aefe47c69501a181ffc68527bb5fb26da6a4b2'
    # START_BLOCK_HEIGHT = 1038078
    # STOP_AT_BLOCK_HEIGHT = None
    # That will trawl every block since issuance to check for any reissuances
    # or burns for the asset so you can validate the amounts shown on the
    # liquid assets page above.

    ###########################################################################
    #              BEFORE RUNNING THE SCRIPT SET THE VALUES BELOW
    ###########################################################################

    # REQUIRED
    # --------
    # Elements RPC Credentials
    # You need to change all 3 after setting them in your elements.conf file.
    # See associated README for example config file format.
    RPC_USER = 'yourusername'
    RPC_PASSWORD = 'yourpassword'
    RPC_PORT = 18885

    # BLOCK RANGE CONTROL
    # -------------------
    # The script will save the last block processed to file and will pick up
    # from there if you set this to True. False will ignore the contents of
    # the LAST_BLOCK file and use START_BLOCK_HEIGHT. If there is no
    # LAST_BLOCK file it will use START_BLOCK_HEIGHT.
    START_FROM_LAST_BLOCK_PROCESSED = True

    # If START_FROM_LAST_BLOCK_PROCESSED is False or the script has not been
    # run before you can specify the initial start block height.
    # This may be useful if you know an initial issuance was done at a
    # particular block height and do not need to process earlier blocks.
    # After running the script the last block processed will saved in the file
    # LAST_BLOCK.
    START_BLOCK_HEIGHT = 0

    # Stop processing at a particular block height (inclusive).
    # Set to None to process until chain tip.
    # If a value is given and the value is equal to the value in LAST_BLOCK the
    # script will exit.
    # If a value is given and the value is lower than the height in
    # the LAST_BLOCK_HEIGHT file it will be ignored and the script will run to
    # chain tip.
    STOP_AT_BLOCK_HEIGHT = None


    # OPTIONAL ASSET ID TO LOOK FOR
    # -----------------------------
    # Set the following to an asset hex if you want to report on a specific
    # asset, otherwise leave it as None to report on all assets:
    # Note: the L-BTC asset id is 6f0279e9ed041c3d710a9f57d0c02928416460c4b722ae3457a11eec381c526d
    # This script will track burns of L-BTC but not pegs in or out yet.
    ASSET_ID = None

    ###########################################################################
    #              BEFORE RUNNING THE SCRIPT SET THE VALUES ABOVE
    ###########################################################################

    block_count = 0
    block_hash = ''
    rpc_ready = False
    end_of_chain = False
    block_height = START_BLOCK_HEIGHT
    saved_block_height = None

    if START_FROM_LAST_BLOCK_PROCESSED:
        saved_block_height = readLastBlockHeight()
        if saved_block_height:
            if STOP_AT_BLOCK_HEIGHT:
                if saved_block_height > STOP_AT_BLOCK_HEIGHT:
                    # If the last block processed is greater than the stop height
                    # process up to chain tip instead.
                    STOP_AT_BLOCK_HEIGHT = None
                if saved_block_height == STOP_AT_BLOCK_HEIGHT:
                    print(f'LAST_BLOCK value is {saved_block_height} and so is STOP_AT_BLOCK_HEIGHT. Exiting.')
                    print(f'Note: set STOP_AT_BLOCK_HEIGHT to None to process to chain tip.')
                    sys.exit()
            if saved_block_height > START_BLOCK_HEIGHT:
                # If the last block processed is greater than the start height
                # process from last block processed. This avoids writing duplicate
                # entries to the asset files.
                block_height = saved_block_height + 1

    message_block_stop_at = 'chain tip'
    if STOP_AT_BLOCK_HEIGHT:
        message_block_stop_at = f'block {str(STOP_AT_BLOCK_HEIGHT)}'

    print(f'Will process from block {block_height} to {message_block_stop_at}.')
    print('Do you want to start processing blocks? (y/n)')
    x = input()
    if x.upper() == 'N' or x.upper() == 'No':
        print(f'Exiting.')
        sys.exit()
    print(f'Processing...')

    # Delete any old asset files if we are starting from genesis:
    if block_height == 0:
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
    last_existing_block = None

    while not end_of_chain:
        try:
            print(f'Processing block at height {block_height}')
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
                    print(f'No block at height {block_height}. Stopping.')
                else:
                    print(f'Error: {e.message}')
            else:
                print(f'Error: {e}')
            end_of_chain = True
    if last_existing_block:
        print(f'Last block processed was at height {last_existing_block}. Saved last block height to "LAST_BLOCK" file.')
        writeLastBlockHeight(last_existing_block)

def readLastBlockHeight():
    if Path('LAST_BLOCK').exists():
        with open('LAST_BLOCK', 'r') as f:
            return int(f.read())
    else:
        return None

def writeLastBlockHeight(block_height):
    with open('LAST_BLOCK', 'w') as f:
        f.write(str(block_height))

def writeBurn(burn, block_height):
    Path('assets').mkdir(parents=True, exist_ok=True)
    asset_hex = burn['asset']
    with open(f'assets/{asset_hex}', 'a') as f:
        amount = burn['value']
        action = 'BURN'
        f.write(f'{action}\n')
        f.write('-' * len(action))
        f.write('\n')
        f.write(f'Asset Hex: {asset_hex}\n')
        f.write(f'Amount: {amount}\n')
        f.write(f'Block: {block_height}\n')
        f.write('\n')

def writeIssueOrReissue(issuance, block_height):
    Path('assets').mkdir(parents=True, exist_ok=True)
    asset_hex = issuance['asset']
    with open(f'assets/{asset_hex}', 'a') as f:
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
        f.write(f'{issuance_reissuance} ({issuance_type})\n')
        f.write('-' * len(f'{issuance_reissuance} ({issuance_type})'))
        f.write('\n')
        f.write(f'Asset Hex: {asset_hex}\n')
        if not is_reissuance:
            f.write(f'Token Hex: {token_hex}\n')
        f.write(f'{asset_amount_type}: {str(asset_amount)}\n')
        if not is_reissuance:
            if token_amount:
                f.write(f'{token_amount_type}: {str(token_amount)}\n')
            else:
                f.write(f'{token_amount_type}: {0}\n')
        f.write(f'Block: {block_height}\n')
        f.write('\n')

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
