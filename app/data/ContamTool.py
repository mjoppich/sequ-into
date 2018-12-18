import argparse
import json
import os

import re
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt

ap = argparse.ArgumentParser(description='--reads file1.fastq --cont file2.fasta file3.fasta')

ap.add_argument("--reads", nargs='+', required=True, help="path to tde read file")
ap.add_argument('--cont', nargs='+', help="path to tde fasta file(s)", required=True)
ap.add_argument("--transcript", nargs="+", required=False, help = "path to tde trascriptomic read files")

ap.add_argument('--o', help="path to tde output directory", required=True)

ap.add_argument("--prefix", help="", required=True)

ap.add_argument('--extract_prefix', type=str, required=False)
ap.add_argument('--extract_not_aligned',  nargs='+', help="path to all fasta files to witch reads did not match", required=False)
ap.add_argument('--extract_aligned',  nargs='+', help="path to all fasta files to witch reads match", required=False)

ap.add_argument("--no_images", default=False, action="store_true", required=False)

args = vars(ap.parse_args())
read_file = args["reads"]
cont_file = args["cont"]
proof_transcript = []
proof_transcript = args['transcript']
output_dir = args["o"]
prefix = args["prefix"]

extracted_not_aligned = args["extract_not_aligned"]
extracted_aligned = args["extract_aligned"]
extract_prefix = args["extract_prefix"]
makeImages = not args['no_images'] 

if prefix[-1] != "_":
    prefix += "_"

if not os.path.exists(output_dir):
    os.mkdir(output_dir)

for rf in read_file:
    if not rf.endswith(".fastq"):
        print('Please enter contamination in fastq format \n *Please no spaces in file name!*')
        exit()

    if not os.path.isfile(rf):
        print('Read file does not exist \n *Please no spaces in file name!*')
        exit()

for rf in cont_file:
    if not rf.endswith(".fasta"):
        print('Please enter contamination in fasta format \n *Please no spaces in file name!*')
        exit()

    if not os.path.isfile(rf):
        print('Contamination file does not exist \n *Please no spaces in file name!*')
        exit()


def makeReport(resDict, fname):

    outHTML = """
    <html>
    <head>
    <title>sequ-into Overview</title>
    <style>
    img {
        display: block;
        margin-left: auto;
        margin-right: auto }

    table {
    border-collapse: collapse;
    width: 100%;
    }

    th, td {
    text-align: left;
    padding: 8px;
    }

    tr:nth-child(even){background-color: #f2f2f2}

    th {
    background-color: #4CAF50;
    color: white;
    }

    body {
        font-family: Arial, Helvetica, sans-serif;
    }
    </style> 
    </head>
    <body>
    """

    outHTML += "<h1>sequ-into report: "+os.path.basename(fname)+"</h1>" + "\n"

    outHTML += "<h2>Alignment Statistics</h2>" + "\n"

    outHTML += "<table><tbody>" + "\n"
    outHTML += "<tr><th>Statistics</th><th>Value</th><th>Rel. Value</th></tr>" + "\n"
    outHTML += "<tr><td>{tdesc}</td><td>{tval:8,d}</td><td>{rval:.5f}</td></tr>".format(tdesc="Total Reads", tval=resDict["totalReads"], rval=1.0) + "\n"
    outHTML += "<tr><td>{tdesc}</td><td>{tval:8,d}</td><td>{rval:.5f}</td></tr>".format(tdesc="Aligned Reads", tval=resDict["alignedReads"], rval=resDict["alignedReads"]/resDict["totalReads"]) + "\n"
    outHTML += "<tr><td>{tdesc}</td><td>{tval:8,d}</td><td>{rval:.5f}</td></tr>".format(tdesc="Unaligned Reads", tval=resDict["totalReads"]-resDict["alignedReads"], rval=(resDict["totalReads"]-resDict["alignedReads"])/resDict["totalReads"]) + "\n"
    outHTML += "<tr><td>{tdesc}</td><td>{tval:8,d}</td><td>{rval:.5f}</td></tr>".format(tdesc="Total Bases", tval=resDict["totalBases"], rval=1.0) + "\n"
    outHTML += "<tr><td>{tdesc}</td><td>{tval:8,d}</td><td>{rval:.5f}</td></tr>".format(tdesc="Alignment Bases", tval=resDict["alignmentBases"], rval=resDict["alignmentBases"]/resDict["totalBases"]) + "\n"
    outHTML += "<tr><td>{tdesc}</td><td>{tval:8,d}</td><td>{rval:.5f}</td></tr>".format(tdesc="Aligned Length", tval=resDict["alignedLength"], rval=resDict["alignedLength"]/resDict["totalBases"]) + "\n"
    outHTML += "</tbody></table>"


    outHTML += "<h2>Read Length Distribution (all reads)</h2>" + "\n"
    outHTML += "<img src=\"{tget}\"/>".format(tget=os.path.basename(resDict["readLengthPlot"])) + "\n"

    outHTML += "<h2>Read Length Distribution (reads <= 10kbp)</h2>" + "\n"
    outHTML += "<img src=\"{tget}\"/>".format(tget=os.path.basename(resDict["readLengthPlotSmall"])) + "\n"

    outHTML += "<h2>Aligned Reads Fraction</h2>" + "\n"
    outHTML += "<img src=\"{tget}\"/>".format(tget=os.path.basename(resDict["readsPie"])) + "\n"

    outHTML += "<h2>Aligned Bases Fraction</h2>" + "\n"
    outHTML += "<img src=\"{tget}\"/>".format(tget=os.path.basename(resDict["basesPie"])) + "\n"

    with open(resDict['overviewUrl'], 'w') as fout:

        fout.write(outHTML)



# Mapper/Aligner

import mappy as mp

refFile2Aligner = {}

# SAM FILE BEARBEITUNG
sam_file_to_dict = dict()
fasta_file_to_dict = dict()

for refFileIdx, refFile in enumerate(cont_file):

    a = mp.Aligner(refFile)  # load or build index
    if not a:
        raise Exception("ERROR: failed to load/build index")


    alignedLength = 0


    totalBases = 0
    alignedBases = 0
    alignmentBases = 0
    
    totalReads = 0
    alignedReads = 0

    idAlignedReads = []
    idNotAlignedReads = []
    
    fasta_outname = re.sub('\W+', '_', refFile)    

    extractAlignedFile = None
    extractUnalignedFile = None

    if extracted_aligned:
        extractAlignedFile = open(os.path.join(output_dir, extract_prefix+ "_aligned_reads.fastq"), "w")

    if extracted_not_aligned:
        extractUnalignedFile = open(os.path.join(output_dir, extract_prefix+ "_aligned_reads.fastq"), "w")

    readLengths = []

    for fastqFile in read_file:
        for name, seq, qual in mp.fastx_read(fastqFile): # read a fasta/q sequence

            hasHit = False

            totalReads += 1
            totalBases += len(seq)
            readLengths.append(len(seq))


            for hit in a.map(seq): # traverse alignments
                hasHit = True

                alignmentBases += hit.r_en-hit.r_st
                alignedBases += hit.mlen

                alignedLength += hit.blen

                #if transcript
                if proof_transcript is not None:
                    if fastqFile in proof_transcript:
                        skipped = 0
                        cigar_array = hit.cigar
                        for i in range(len(cigar_array)):
                            if cigar_array[i][0] == "N":
                                skipped += cigar_array[i][1]
                        alignmentBases = alignmentBases - skipped

                #print("{}\t{}\t{}\t{}".format(hit.ctg, hit.r_st, hit.r_en, hit.cigar_str))

            if not hasHit:
                idNotAlignedReads.append(name)

                if extractUnalignedFile != None:
                    extractUnalignedFile.write("@"+name + "\n" + seq + "\n+\n" + qual + "\n")

            else:
                idAlignedReads.append(name)
                alignedReads += 1

                if extractAlignedFile != None:
                    extractAlignedFile.write("@"+name + "\n" + seq + "\n+\n" + qual + "\n")

    if refFileIdx == 0:

        try:
            readsLengthPlot = os.path.join(output_dir,prefix+"reads_length.png")
            readsLengthPlot10k = os.path.join(output_dir,prefix+"reads_length_10000.png")

            plt.figure(0)
            plt.ylabel('Frequency', fontsize=10)
            plt.xlabel('Length of reads', fontsize=10)
            plt.title('Length frequencies of all reads', fontsize=12)
            plt.hist(readLengths, bins=100, color='green')
            plt.savefig(readsLengthPlot)
            plt.close()

            plt.figure(1)
            plt.ylabel('Frequency', fontsize=10)
            plt.xlabel('Length of reads', fontsize=10)
            plt.title('Length frequencies of all reads', fontsize=12)
            plt.hist([x for x in readLengths if x < 10000], bins=100, color='green')
            plt.savefig(readsLengthPlot10k)
            plt.close()

        except ValueError:
            print('Some problems witd read file: Secondary ID line in FASTQ file doesnot start witd ''+''.')
            exit()


    readPiePlot = os.path.join(output_dir,prefix + "_" + fasta_outname + "read_pie.png")
    basesPiePlot = os.path.join(output_dir,prefix + "_" + fasta_outname + "bases_pie.png")

    if makeImages:
        labels = ('Aligned \n Reads \n (n={acount})'.format(acount=alignedReads), 'Unaligned \n Reads \n (n={acount})'.format(acount=totalReads-alignedReads))
        plt.pie([alignedReads, (totalReads-alignedReads)], explode=(0,0), labels=labels, colors=['gold', 'yellowgreen'],
                autopct='%1.1f%%', shadow=True, startangle=140, textprops={'fontsize': 13})
        plt.axis('equal')

        plt.savefig(readPiePlot)
        plt.close()

        labels = ('Aligned \n Bases \n (n={acount})'.format(acount=alignedLength), 'Unaligned \n Bases \n (n={acount})'.format(acount=totalBases-alignedLength))
        plt.pie([alignedLength, (totalBases - alignedLength)], explode=(0, 0), labels=labels, colors=['lightcoral', 'lightskyblue'],
                autopct='%1.1f%%', shadow=True, startangle=140, textprops={'fontsize': 13})
        plt.axis('equal')
        plt.savefig(basesPiePlot)
        plt.close()


    tmp_dict = dict(
                    totalReads=totalReads,
                    alignedReads=alignedReads,
                    totalBases=totalBases,
                    alignmentBases=alignmentBases,
                    alignedLength=alignedLength
                    )
                    #idAlignedReads=idAlignedReads,
                    #idNotAlignedReads=idNotAlignedReads

    if makeImages:
        tmp_dict["readLengthPlot"] = readsLengthPlot
        tmp_dict["readLengthPlotSmall"] = readsLengthPlot10k
        tmp_dict["readsPie"] = readPiePlot
        tmp_dict["basesPie"] = basesPiePlot
        tmp_dict["refs"] = [refFile]
        tmp_dict["overviewUrl"] = os.path.join(output_dir,prefix + "_" + fasta_outname + "overview.html")


        makeReport(tmp_dict, refFile)

    fasta_file_to_dict[refFile]=tmp_dict

print(json.dumps(fasta_file_to_dict))
