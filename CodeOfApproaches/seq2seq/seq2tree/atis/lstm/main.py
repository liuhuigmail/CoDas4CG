import argparse
import time
import pickle as pkl
import util
import os
import time
import numpy as np
from tree import Tree

import torch
import torch.nn as nn
import torch.nn.init as init
import torch.nn.functional as F
from torch import optim
import random

class LSTM(nn.Module):
    def __init__(self, opt):
        super(LSTM, self).__init__()
        self.opt = opt
        self.i2h = nn.Linear(opt.rnn_size, 4 * opt.rnn_size)
        self.h2h = nn.Linear(opt.rnn_size, 4*opt.rnn_size)
        if opt.dropoutrec > 0:
            self.dropout = nn.Dropout(opt.dropoutrec)

    def forward(self, x, prev_c, prev_h):
        gates = self.i2h(x) \
            + self.h2h(prev_h)
        ingate, forgetgate, cellgate, outgate = gates.chunk(4, 1)
        ingate = F.sigmoid(ingate)
        forgetgate = F.sigmoid(forgetgate)
        cellgate = F.tanh(cellgate)
        outgate = F.sigmoid(outgate)
        if self.opt.dropoutrec > 0:
            cellgate = self.dropout(cellgate)
        cy = (forgetgate * prev_c) + (ingate * cellgate)
        hy = outgate * F.tanh(cy)  # n_b x hidden_dim
        return cy, hy

class EncoderRNN(nn.Module):
    def __init__(self, opt, input_size):
        super(EncoderRNN, self).__init__()
        self.opt = opt
        self.hidden_size = opt.rnn_size
        self.embedding = nn.Embedding(input_size, self.hidden_size)
        self.lstm = LSTM(self.opt)
        if opt.dropout > 0:
            self.dropout = nn.Dropout(opt.dropout)

    def forward(self, input_src, prev_c, prev_h):
        src_emb = self.embedding(input_src) # batch_size x src_length x emb_size
        if self.opt.dropout > 0:
            src_emb = self.dropout(src_emb)
        prev_cy, prev_hy = self.lstm(src_emb, prev_c, prev_h)
        return prev_cy, prev_hy

class DecoderRNN(nn.Module):
    def __init__(self, opt, output_size):
        super(DecoderRNN, self).__init__()
        self.opt = opt
        self.hidden_size = opt.rnn_size

        self.embedding = nn.Embedding(output_size, self.hidden_size)
        self.lstm = LSTM(self.opt)
        self.linear = nn.Linear(self.hidden_size, output_size)
        if opt.dropout > 0:
            self.dropout = nn.Dropout(opt.dropout)

        self.softmax = nn.LogSoftmax(dim=1)

    def forward(self, input, prev_c, prev_h):
        output = self.embedding(input)
        if self.opt.dropout > 0:
            output = self.dropout(output)
        next_c, next_h = self.lstm(output, prev_c, prev_h)
        if self.opt.dropout > 0:
            next_h = self.dropout(next_h)
        h2y = self.linear(next_h)
        pred = self.softmax(h2y)
        return pred, next_c, next_h

def eval_training(opt, train_loader, encoder, decoder, encoder_optimizer, decoder_optimizer, criterion, using_gpu, word_manager, form_manager):
    encoder_optimizer.zero_grad()
    decoder_optimizer.zero_grad()
    enc_batch, enc_len_batch, dec_tree_batch = train_loader.random_batch()
    enc_max_len = enc_batch.size(1)

    enc_s = {}
    for j in range(opt.enc_seq_length + 1):
        enc_s[j] = {}

    dec_s = {}
    for i in range(opt.dec_seq_length + 1):
        dec_s[i] = {}
        for j in range(opt.dec_seq_length + 1):
            dec_s[i][j] = {}

    for i in range(1, 3):
        enc_s[0][i] = torch.zeros((opt.batch_size, opt.rnn_size), dtype=torch.float, requires_grad=True)
        if using_gpu:
            enc_s[0][i] = enc_s[0][i].cuda()

    for i in range(enc_max_len):
        enc_s[i+1][1], enc_s[i+1][2] = encoder(enc_batch[:,i], enc_s[i][1], enc_s[i][2])

    # tree decode
    queue_tree = {}
    for i in range(1, opt.batch_size+1):
        queue_tree[i] = []
        #string1 = dec_tree_batch[i-1].to_string()
        #print(string1)
        queue_tree[i].append({"tree" : dec_tree_batch[i-1], "parent": 0, "child_index": 1})
    loss = 0
    cur_index, max_index = 1,1
    dec_batch = {}
    #print(queue_tree[1][0]["tree"].to_string());exit()
    while (cur_index <= max_index):
        #print(cur_index)
        # build dec_batch for cur_index
        max_w_len = -1
        batch_w_list = []
        for i in range(1, opt.batch_size+1):
            w_list = []
            if (cur_index <= len(queue_tree[i])):
                t = queue_tree[i][cur_index - 1]["tree"]
                for ic in range (t.num_children):
                    #print("children ")
                    #print(ic +1)
                    if isinstance(t.children[ic], Tree):
                        #print("appending")
                        w_list.append(3)
                        queue_tree[i].append({"tree" : t.children[ic], "parent" : cur_index, "child_index": ic + 1})
                    else:
                        w_list.append(t.children[ic])
                if len(queue_tree[i]) > max_index:
                    max_index = len(queue_tree[i])
            if len(w_list) > max_w_len:
                max_w_len = len(w_list)
            batch_w_list.append(w_list)
        dec_batch[cur_index] = torch.zeros((opt.batch_size, max_w_len + 2), dtype=torch.long)
        for i in range(opt.batch_size):
            w_list = batch_w_list[i]
            if len(w_list) > 0:
                for j in range(len(w_list)):
                    dec_batch[cur_index][i][j+1] = w_list[j]
                # add <S>, <E>
                if cur_index == 1:
                    dec_batch[cur_index][i][0] = 0
                else:
                    dec_batch[cur_index][i][0] = form_manager.get_symbol_idx('(')
                dec_batch[cur_index][i][len(w_list) + 1] = 1
        #print(dec_batch[cur_index])
        # initialize first decoder unit hidden state (zeros)
        if using_gpu:
            dec_batch[cur_index] = dec_batch[cur_index].cuda()
        # initialize using encoding results
        for j in range(1, 3):
            dec_s[cur_index][0][j] = torch.zeros((opt.batch_size, opt.rnn_size), dtype=torch.float, requires_grad=True)
            if using_gpu:
                dec_s[cur_index][0][j] = dec_s[cur_index][0][j].cuda()

        if cur_index == 1:
            for i in range(opt.batch_size):
                dec_s[1][0][1][i, :] = enc_s[enc_len_batch[i]][1][i, :]
                dec_s[1][0][2][i, :] = enc_s[enc_len_batch[i]][2][i, :]

        else:
            for i in range(1, opt.batch_size+1):
                if (cur_index <= len(queue_tree[i])):
                    par_index = queue_tree[i][cur_index - 1]["parent"]
                    child_index = queue_tree[i][cur_index - 1]["child_index"]
                    #print("parent child")
                    #print(par_index)
                    #print(child_index)
                    dec_s[cur_index][0][1][i-1,:] = \
                        dec_s[par_index][child_index][1][i-1,:]
                    dec_s[cur_index][0][2][i-1,:] = dec_s[par_index][child_index][2][i-1,:]
        #loss = 0
        #prev_c, prev_h = dec_s[cur_index, 0, 0,:,:], dec_s[cur_index, 0, 1,:,:]
        #pred_matrix = np.ndarray((20, dec_batch[cur_index].size(1)-1), dtype=object)
        gold_string = " "
        for i in range(dec_batch[cur_index].size(1) - 1):
            #print(i)
            pred, dec_s[cur_index][i+1][1], dec_s[cur_index][i+1][2] = decoder(dec_batch[cur_index][:,i], dec_s[cur_index][i][1], dec_s[cur_index][i][2])
            #print(dec_batch[cur_index][:,i+1])
            #pred_max = pred.argmax(1)
            #pred_ints = [int(p) for p in pred_max]
            #gold = dec_batch[cur_index][:,i+1]
            #gold_ints = [int(p) for p in gold]
            ##print(gold_ints)
            ##print("prediction:")
            ##print(pred_max)
            ##print(dec_batch[cur_index][:,i+1])
            ##pred_strings = [form_manager.get_idx_symbol(int(p)) for p in pred_max]
            ##gold_strings = [form_manager.get_idx_symbol(int(p)) for p in dec_batch[cur_index][:,i+1]]
            #gold_string += form_manager.get_idx_symbol(int(dec_batch[cur_index][0,i+1]))
            #gold_string += " "
            ##print("i: ")
            ##print(i)
            ##print(pred_strings)
            #print(gold_strings)
            #pred_matrix[:,i] = pred_strings
            #pred, prev_c, prev_h = decoder(dec_batch[cur_index][:,i], dec_s[cur_index, i, 0, :,:], dec_s[cur_index, i, 1, :, :]);
            #dec_s[cur_index, i+1, 0,:,:], dec_s[cur_index, i+1, 1,:,:] = prev_c.clone(), prev_h.clone()
            loss += criterion(pred, dec_batch[cur_index][:,i+1])
        #print("start")
        #print(gold_string)
        #print("between")
        #print(dec_batch[cur_index][0, i+1])
        #print("end")

        cur_index = cur_index + 1
    #input_string = [form_manager.get_idx_symbol(int(p)) for p in enc_batch[0,:]]
    #print("===========\n")
    #print("input string: {}\n".format(input_string))
    #print("predicted string: {}\n".format(pred_matrix[0,:]))
    #print("===========\n")

    loss = loss / opt.batch_size
    loss.backward()
    torch.nn.utils.clip_grad_value_(encoder.parameters(),opt.grad_clip)
    torch.nn.utils.clip_grad_value_(decoder.parameters(),opt.grad_clip)
    encoder_optimizer.step()
    decoder_optimizer.step()
    #print("end eval training \n ")
    #print("=====================\n")
    return loss


def main(opt):
    random.seed(opt.seed)
    np.random.seed(opt.seed)
    torch.manual_seed(opt.seed)
    managers = pkl.load( open("{}/map.pkl".format(opt.data_dir), "rb" ) )
    word_manager, form_manager = managers
    using_gpu = False
    if opt.gpuid > -1:
        using_gpu = True
    encoder = EncoderRNN(opt, word_manager.vocab_size)
    decoder = DecoderRNN(opt, form_manager.vocab_size)
    if using_gpu:
        encoder = encoder.cuda()
        decoder = decoder.cuda()
    # init parameters
    for name, param in encoder.named_parameters():
        if param.requires_grad:
            init.uniform_(param, -opt.init_weight, opt.init_weight)
    for name, param in decoder.named_parameters():
        if param.requires_grad:
            init.uniform_(param, -opt.init_weight, opt.init_weight)

    #model_parameters = filter(lambda p: p.requires_grad, encoder.parameters())
    #params_encoder = sum([np.prod(p.size()) for p in model_parameters])
    #model_parameters = filter(lambda p: p.requires_grad, decoder.parameters())
    #params_decoder = sum([np.prod(p.size()) for p in model_parameters])
    #print(params_encoder)
    #print(params_decoder)
    #print(params_encoder + params_decoder);
    # 342400
    # 343655
    # 686055
    # number of parameters in the encoder model: 342400
    # number of parameters in the decoder model: 343655
    # number of parameters in the model: 686055

    ##-- load data
    train_loader = util.MinibatchLoader(opt, 'train', using_gpu)

    if not os.path.exists(opt.checkpoint_dir):
        os.makedirs(opt.checkpoint_dir)

    ##-- start training
    step = 0
    epoch = 0
    optim_state = {"learningRate" : opt.learning_rate, "alpha" :  opt.decay_rate}
    # default to rmsprop
    if opt.opt_method == 0:
        print("using RMSprop")
        encoder_optimizer = optim.RMSprop(encoder.parameters(),  lr=optim_state["learningRate"], alpha=optim_state["alpha"])
        decoder_optimizer = optim.RMSprop(decoder.parameters(),  lr=optim_state["learningRate"], alpha=optim_state["alpha"])
    criterion = nn.NLLLoss(size_average=False, ignore_index=0)

    print("Starting training.")
    encoder.train()
    decoder.train()
    iterations = opt.max_epochs * train_loader.num_batch
    start_time = time.time()
    restarted = False
    # TODO revert back after tests
    #iterations = 2
    for i in range(iterations):
        epoch = i // train_loader.num_batch
        train_loss = eval_training(opt, train_loader, encoder, decoder, encoder_optimizer, decoder_optimizer, criterion, using_gpu, word_manager, form_manager)
        #exponential learning rate decay
        if opt.opt_method == 0:
            if i % train_loader.num_batch == 0 and opt.learning_rate_decay < 1:
                if epoch >= opt.learning_rate_decay_after:
                    decay_factor = opt.learning_rate_decay
                    optim_state["learningRate"] = optim_state["learningRate"] * decay_factor #decay it
                    for param_group in encoder_optimizer.param_groups:
                        param_group['lr'] = optim_state["learningRate"]
                    for param_group in decoder_optimizer.param_groups:
                        param_group['lr'] = optim_state["learningRate"]
        if (epoch == opt.restart) and not restarted:
            restarted = True
            optim_state["learningRate"] = opt.learning_rate
            for param_group in encoder_optimizer.param_groups:
                param_group['lr'] = optim_state["learningRate"]
                param_group['momentum'] = 0
            for param_group in decoder_optimizer.param_groups:
                param_group['lr'] = optim_state["learningRate"]
                param_group['momentum'] = 0


        if i % opt.print_every == 0:
            end_time = time.time()
            print("{}/{}, train_loss = {}, time since last print = {}".format( i, iterations, train_loss, (end_time - start_time)/60))
            start_time = time.time()

        #on last iteration
        if i == iterations -1:
            checkpoint = {}
            checkpoint["encoder"] = encoder
            checkpoint["decoder"] = decoder
            checkpoint["opt"] = opt
            checkpoint["i"] = i
            checkpoint["epoch"] = epoch
            torch.save(checkpoint, "{}/model_seq2seq".format(opt.checkpoint_dir))

        if train_loss != train_loss:
            print('loss is NaN.  This usually indicates a bug.')
            break

if __name__ == "__main__":
    start = time.time()
    main_arg_parser = argparse.ArgumentParser(description="parser")
    main_arg_parser.add_argument('-gpuid', type=int, default=0, help='which gpu to use. -1 = use CPU')
    main_arg_parser.add_argument('-data_dir', type=str, default='../data/', help='data path')
    main_arg_parser.add_argument('-seed',type=int,default=123,help='torch manual random number generator seed')
    main_arg_parser.add_argument('-checkpoint_dir',type=str, default= 'checkpoint_dir', help='output directory where checkpoints get written')
    main_arg_parser.add_argument('-savefile',type=str, default='save',help='filename to autosave the checkpont to. Will be inside checkpoint_dir/')
    main_arg_parser.add_argument('-print_every',type=int, default=2000,help='how many steps/minibatches between printing out the loss')
    main_arg_parser.add_argument('-rnn_size', type=int,default=250, help='size of LSTM internal state')
    main_arg_parser.add_argument('-num_layers', type=int, default=1, help='number of layers in the LSTM')
    main_arg_parser.add_argument('-dropout',type=float, default=0.4,help='dropout for regularization, used after each RNN hidden layer. 0 = no dropout')
    main_arg_parser.add_argument('-dropoutrec',type=float,default=0,help='dropout for regularization, used after each c_i. 0 = no dropout')
    main_arg_parser.add_argument('-enc_seq_length',type=int, default=60,help='number of timesteps to unroll for')
    main_arg_parser.add_argument('-dec_seq_length',type=int, default=220,help='number of timesteps to unroll for')
    main_arg_parser.add_argument('-batch_size',type=int, default=20,help='number of sequences to train on in parallel')
    #main_arg_parser.add_argument('-batch_size',type=int, default=2,help='number of sequences to train on in parallel')
    main_arg_parser.add_argument('-max_epochs',type=int, default=130,help='number of full passes through the training data')
    main_arg_parser.add_argument('-opt_method', type=int,default=0,help='optimization method: 0-rmsprop 1-sgd')
    main_arg_parser.add_argument('-learning_rate',type=float, default=0.006,help='learning rate')
    main_arg_parser.add_argument('-init_weight',type=float, default=0.08,help='initailization weight')
    main_arg_parser.add_argument('-learning_rate_decay',type=float, default=0.975,help='learning rate decay')
    main_arg_parser.add_argument('-learning_rate_decay_after',type=int, default=5,help='in number of epochs, when to start decaying the learning rate')
    main_arg_parser.add_argument('-restart',type=int, default=20,help='in number of epochs, when to restart the optimization')
    main_arg_parser.add_argument('-decay_rate',type=float, default=0.95,help='decay rate for rmsprop')
    main_arg_parser.add_argument('-grad_clip',type=int, default=5,help='clip gradients at this value')

    args = main_arg_parser.parse_args()
    main(args)
    end = time.time()
    print("total time: {} minutes\n".format((end - start)/60))
