import sys
d=open(sys.argv[1],'rb').read(); base=0x06004000
fs=sorted((int(l.split()[1],16),int(l.split()[4])) for l in open(sys.argv[2]) if l.startswith('F '))
prev=base; tot=0
for a,s in fs+[(base+len(d),0)]:
    if a-prev>=256:
        seg=d[prev-base:a-base]
        rts=sum(1 for i in range(0,len(seg)-1,2) if seg[i:i+2]==b'\x00\x0b')
        pr=sum(1 for i in range(0,len(seg)-1,2) if seg[i:i+2] in (b'\x4f\x22',b'\x2f\xe6',b'\x2f\x86'))
        print(hex(prev),hex(a),a-prev,'rts',rts,'push',pr); tot+=a-prev
    prev=max(prev,a+s)
print('gap total',tot)
